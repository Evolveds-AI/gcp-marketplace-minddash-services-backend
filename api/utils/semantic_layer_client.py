from typing import Any, Dict, List, Optional

import yaml

from api.services.gcs_client import (
    download_text_from_gcs,
    get_cached_semantic,
    set_cached_semantic,
)


class SemanticLayerClient:
    """Cliente ligero para descargar y consultar la capa semántica (YAML) con caché."""

    def __init__(self, gs_uri: str, ttl_seconds: int = 900):
        self.gs_uri = gs_uri
        self.ttl_seconds = ttl_seconds
        self._semantic: Optional[Dict[str, Any]] = None

    def _ensure_loaded(self) -> None:
        if self._semantic is not None:
            return
        cached = get_cached_semantic(self.gs_uri, ttl_seconds=self.ttl_seconds)
        if cached is not None:
            self._semantic = yaml.safe_load(cached)
            return
        if not self.gs_uri.startswith("gs://"):
            raise ValueError("gs_uri debe comenzar con gs://")
        without_scheme = self.gs_uri[len("gs://") :]
        if "/" not in without_scheme:
            raise ValueError("gs_uri invalido: falta object path")
        bucket_name, object_path = without_scheme.split("/", 1)
        content, _ = download_text_from_gcs(bucket_name, object_path)
        set_cached_semantic(self.gs_uri, content)
        self._semantic = yaml.safe_load(content)

    def get_semantic(self) -> Dict[str, Any]:
        """Devuelve el dict completo del YAML parseado."""
        self._ensure_loaded()
        return self._semantic or {}

    def list_tables(self) -> List[str]:
        self._ensure_loaded()
        datasets: Dict[str, Any] = self._semantic.get("datasets", {})  # type: ignore
        return list(datasets.keys())

    def get_dataset(self, fq_name: str) -> Optional[Dict[str, Any]]:
        self._ensure_loaded()
        return self._semantic.get("datasets", {}).get(fq_name)  # type: ignore

    def get_schema_for_table(self, fq_name: str) -> Dict[str, Any]:
        self._ensure_loaded()
        ds = self.get_dataset(fq_name)
        if not ds:
            return {}
        dims = ds.get("dimensions", {})
        meas = ds.get("measures", {})
        cols = list(dims.keys()) + list(meas.keys())
        # Devolver texto similar a la tool previa
        lines: List[str] = []
        for name in cols:
            if name in dims:
                dtype = dims[name].get("data_type") or "string"
            else:
                dtype = meas[name].get("data_type") or "number"
            lines.append(f"{name} ({dtype})")
        return {
            "schema_text": "\n".join(lines),
            "time_dimension": ds.get("time_dimension"),
            "primary_key": ds.get("primary_key"),
        }

    def get_profile_text(
        self, fq_name: str, columns: Optional[List[str]] = None
    ) -> Optional[str]:
        """Devuelve el texto de perfil si existe en el YAML (opcionalmente filtrado por columnas)."""
        self._ensure_loaded()
        ds = self.get_dataset(fq_name)
        if not ds:
            return None
        prof = ds.get("profile")
        if not prof:
            return None
        if not columns:
            return prof
        # Normalizar saltos de línea por si vienen escapados en YAML ('\n')
        text = prof
        if "\\n" in prof:
            text = prof.replace("\\n", "\n")
        # filtrar columnas: tomar bloques por columna
        sections: Dict[str, List[str]] = {}
        current: List[str] = []
        current_name: Optional[str] = None
        for line in text.splitlines():
            if line.startswith("Column: '"):
                if current_name is not None:
                    sections.setdefault(current_name, []).extend(current)
                # iniciar nueva sección
                current = [line]
                try:
                    name_part = line.split("Column: '", 1)[1]
                    current_name = name_part.split("'", 1)[0]
                except Exception:
                    current_name = None
            else:
                current.append(line)
        if current_name is not None:
            sections.setdefault(current_name, []).extend(current)
        wanted = [c for c in (columns or []) if c in sections]
        out_lines: List[str] = []
        for name in wanted:
            out_lines.extend(sections[name])
            out_lines.append("")
        return "\n".join(out_lines).rstrip() if out_lines else None

    def get_profile_json(
        self, fq_name: str, columns: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Devuelve un dict estructurado del perfil si existe en el YAML (opcionalmente filtrado por columnas)."""
        txt = self.get_profile_text(fq_name)
        if not txt:
            return None
        # parseo simple del formato en texto a una estructura por columna
        profile: Dict[str, Any] = {"columns": {}}
        current: Dict[str, Any] = {}
        current_name: Optional[str] = None
        for raw in txt.splitlines():
            line = raw.strip()
            if line.startswith("Column: '"):
                if current_name:
                    profile["columns"][current_name] = current
                current = {}
                try:
                    rest = line.split("Column: '", 1)[1]
                    name, type_part = rest.split("'", 1)
                    dtype = type_part.strip()
                    if dtype.startswith("(") and dtype.endswith(")"):
                        dtype = dtype[1:-1]
                except Exception:
                    name, dtype = "UNKNOWN", ""
                current_name = name
                current["data_type"] = dtype
            elif line.startswith("Count:"):
                try:
                    current.setdefault("stats", {})["count"] = float(
                        line.split(":", 1)[1].strip()
                    )
                except Exception:
                    pass
            elif line.startswith("Min:"):
                current.setdefault("stats", {})["min"] = line.split(":", 1)[1].strip()
            elif line.startswith("Max:"):
                current.setdefault("stats", {})["max"] = line.split(":", 1)[1].strip()
            elif line.startswith("Avg:"):
                current.setdefault("stats", {})["avg"] = line.split(":", 1)[1].strip()
            elif line.startswith("All possible values are shown:") or line.startswith(
                "The 10 most frequent values are shown"
            ):
                current["note"] = line
            elif ":" in line and not line.startswith("-") and not line.startswith("("):
                # posibles entradas "valor: freq" para texto
                parts = line.split(":", 1)
                val = parts[0].strip()
                try:
                    freq = int(parts[1].strip())
                    current.setdefault("stats", {}).setdefault("top_values", []).append(
                        {"value": val, "freq": freq}
                    )
                except Exception:
                    pass
        if current_name:
            profile["columns"][current_name] = current
        if columns:
            keep = {k: v for k, v in profile["columns"].items() if k in set(columns)}
            profile["columns"] = keep
        return profile

    def get_relationships(self) -> List[Dict[str, Any]]:
        """Devuelve la lista de relaciones si existen en el YAML; si no, []."""
        self._ensure_loaded()
        rels = []
        try:
            raw = self._semantic.get("relationships")  # type: ignore
            if isinstance(raw, list):
                rels = raw
        except Exception:
            pass
        return rels
