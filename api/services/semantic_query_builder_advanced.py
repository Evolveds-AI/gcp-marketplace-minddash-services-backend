from typing import Any, Dict, List, Optional, Tuple


class QueryBuilderAdvanced:
    """Query builder multi-dataset usando 'relationships' del YAML.

    Espera un 'semantic' cargado desde YAML con:
      semantic['datasets'][fq_name] = {
        'schema','table','dimensions':{name:{'expression',...}}, 'measures':{name:{'expression',...}}
      }
      semantic['relationships'] = [
        {'left_dataset','left_key','right_dataset','right_key','join_type','cardinality'}
      ]
    """

    def __init__(self, semantic: Dict[str, Any], engine: str = "postgres"):
        self.semantic = semantic
        self.engine = engine
        self.datasets: Dict[str, Dict[str, Any]] = semantic.get("datasets", {})
        self.relationships: List[Dict[str, str]] = (
            semantic.get("relationships", []) or []
        )

    def build(
        self,
        dimensions: List[str],  # ['schema.table.field', ...]
        measures: List[str],  # ['schema.table.field', ...]
        filters: Optional[
            List[Dict[str, Any]]
        ] = None,  # [{'dataset_key','field','op','value'}]
        order_by: Optional[List[Tuple[int, str]]] = None,
        limit: Optional[int] = None,
    ) -> str:
        if not dimensions and not measures:
            raise ValueError("No hay campos seleccionados")

        # Parseo de refs 'dataset.field'
        dim_refs = [self._split_ref(r) for r in dimensions]
        met_refs = [self._split_ref(r) for r in measures]
        required_datasets = {ds for ds, _ in dim_refs + met_refs}

        # Alias por dataset
        aliases: Dict[str, str] = {}
        for idx, ds in enumerate(sorted(required_datasets)):
            aliases[ds] = f"t{idx + 1}"

        # FROM + JOINS
        from_sql, join_sql = self._build_from_and_joins(required_datasets, aliases)

        # SELECT
        select_parts: List[str] = []
        for ds, field in dim_refs:
            expr = self._get_expression(ds, field, kind="dimension")
            qualified = self._qualify_expression(aliases[ds], field, expr)
            select_parts.append(f"{qualified} AS {self._ql(field)}")
        for ds, field in met_refs:
            expr = self._get_expression(ds, field, kind="measure")
            qualified = self._qualify_expression(aliases[ds], field, expr)
            select_parts.append(f"{qualified} AS {self._ql(field)}")
        select_sql = "SELECT " + ", ".join(select_parts)

        # WHERE
        where_sql = self._build_where(filters, aliases) if filters else ""

        # GROUP BY si hay medidas
        group_by_sql = ""
        if met_refs and dim_refs:
            group_by_sql = "GROUP BY " + ", ".join(
                str(i) for i in range(1, len(dim_refs) + 1)
            )

        # ORDER BY opcional con validación
        total_cols = len(select_parts)
        if order_by:
            validated: List[str] = []
            for i, d in order_by:
                if not isinstance(i, int) or i < 1 or i > total_cols:
                    raise ValueError(
                        f"ORDER BY posición inválida: {i}; columnas disponibles: 1..{total_cols}"
                    )
                dirc = "DESC" if str(d).upper() == "DESC" else "ASC"
                validated.append(f"{i} {dirc}")
            order_sql = "ORDER BY " + ", ".join(validated)
        else:
            order_sql = ""

        limit_sql = f"LIMIT {limit}" if isinstance(limit, int) else ""

        parts = [select_sql, from_sql]
        if join_sql:
            parts.append(join_sql)
        if where_sql:
            parts.append(where_sql)
        if group_by_sql:
            parts.append(group_by_sql)
        if order_sql:
            parts.append(order_sql)
        if limit_sql:
            parts.append(limit_sql)
        return "\n".join(parts).strip()

    # ---- helpers ----
    def _split_ref(self, ref: str) -> Tuple[str, str]:
        if ref.count(".") < 2:
            raise ValueError(f"Referencia inválida, usar schema.table.field: {ref}")
        parts = ref.split(".")
        dataset = ".".join(parts[0:2])  # schema.table
        field = parts[2]
        if dataset not in self.datasets:
            raise ValueError(f"Dataset no encontrado en YAML: {dataset}")
        return dataset, field

    def _build_from_and_joins(
        self, required: set, aliases: Dict[str, str]
    ) -> Tuple[str, str]:
        if not required:
            # fallback improbable
            any_ds = next(iter(self.datasets.keys()))
            schema = self.datasets[any_ds]["schema"]
            table = self.datasets[any_ds]["table"]
            return (
                f"FROM {self._qi(schema)}.{self._qi(table)} AS {aliases.get(any_ds, 't1')}",
                "",
            )

        # base
        base = next(iter(required))
        required = set(required)
        connected = {base}
        base_schema = self.datasets[base]["schema"]
        base_table = self.datasets[base]["table"]
        from_sql = (
            f"FROM {self._qi(base_schema)}.{self._qi(base_table)} AS {aliases[base]}"
        )

        if len(required) == 1:
            return from_sql, ""

        # construir joins por BFS sobre relationships
        joins: List[str] = []
        remaining = required - {base}
        # Prepara índice por par de datasets (bidireccional)
        edges: List[Dict[str, str]] = self.relationships

        attempts = 0
        while remaining and attempts < 1000:
            attempts += 1
            progress = False
            for r in edges:
                L = r.get("left_dataset")
                R = r.get("right_dataset")
                if not L or not R:
                    continue
                if (L in connected and R in remaining) or (
                    R in connected and L in remaining
                ):
                    left_ds, right_ds = (L, R) if L in connected else (R, L)
                    left_key = r.get("left_key") if left_ds == L else r.get("right_key")
                    right_key = (
                        r.get("right_key") if right_ds == R else r.get("left_key")
                    )
                    join_type = (r.get("join_type") or "inner").upper()
                    left_alias = aliases[left_ds]
                    right_alias = aliases[right_ds]
                    on_cond = f"{left_alias}.{self._qi(left_key)} = {right_alias}.{self._qi(right_key)}"
                    # tabla derecha
                    rs = self.datasets[right_ds]["schema"]
                    rt = self.datasets[right_ds]["table"]
                    joins.append(
                        f"{join_type} JOIN {self._qi(rs)}.{self._qi(rt)} AS {right_alias} ON {on_cond}"
                    )
                    connected.add(right_ds)
                    remaining.remove(right_ds)
                    progress = True
                    if not remaining:
                        break
            if not progress:
                raise ValueError(
                    f"No se pudieron conectar todos los datasets requeridos: {remaining}"
                )
        return from_sql, "\n".join(joins)

    def _get_expression(self, dataset_key: str, field: str, kind: str) -> str:
        ds = self.datasets.get(dataset_key) or {}
        section = ds.get("dimensions" if kind == "dimension" else "measures", {})
        if field not in section:
            raise ValueError(
                f"Campo no encontrado en {kind}s de {dataset_key}: {field}"
            )
        expr = section[field].get("expression")
        if not expr:
            # fallback a nombre de columna simple
            return self._qi(field)
        return expr

    def _qualify_expression(self, alias: str, field: str, expression: str) -> str:
        # Si la expresión es exactamente un identificador quoted, calificar
        stripped = expression.strip()
        if self._is_simple_identifier(stripped, field):
            return f"{alias}.{self._qi(field)}"
        # Reemplazo simple del identificador con calificación, si aparece en comillas
        replaced = stripped.replace(self._qi(field), f"{alias}.{self._qi(field)}")
        return replaced

    def _is_simple_identifier(self, expr: str, field: str) -> bool:
        # Verificar si la expresión es exactamente el identificador citado según el engine
        return expr in (self._qi(field), f"`{field}`", f"[{field}]", f'"{field}"')

    def _build_where(
        self, filters: List[Dict[str, Any]], aliases: Dict[str, str]
    ) -> str:
        parts: List[str] = []
        for f in filters:
            ds = f.get("dataset_key")
            field = f.get("field")
            op = (f.get("op") or "").upper()
            val = f.get("value")
            if not ds or not field or not op:
                raise ValueError("Filtro inválido: falta dataset/field/op")
            if ds not in aliases:
                raise ValueError(f"Filtro refiere a dataset no requerido: {ds}")
            left = f"{aliases[ds]}.{self._qi(field)}"
            if op in ("=", "!=", ">", "<", ">=", "<="):
                parts.append(f"{left} {op} {self._lit(val)}")
            elif op == "IN" and isinstance(val, list):
                parts.append(f"{left} IN ({', '.join(self._lit(v) for v in val)})")
            elif op == "BETWEEN" and isinstance(val, list) and len(val) == 2:
                parts.append(
                    f"{left} BETWEEN {self._lit(val[0])} AND {self._lit(val[1])}"
                )
            elif op == "LIKE" and isinstance(val, str):
                parts.append(f"{left} LIKE {self._lit(val)}")
            else:
                raise ValueError(f"Operador/valor inválido en filtro: {f}")
        return ("WHERE " + " AND ".join(parts)) if parts else ""

    def _qi(self, ident: Optional[str]) -> str:
        if ident is None:
            return '""'
        if self.engine in ("mysql", "bigquery", "mariadb", "snowflake", "clickhouse"):
            return f"`{ident}`"
        elif self.engine in ("mssql", "synapsemssql"):
            return f"[{ident}]"
        else:
            return f'"{ident}"'  # postgres, redshift, aurora, aurorapostgres, auroramysql, hana, oracle, teradata

    def _ql(self, label: str) -> str:
        return f'"{label}"'

    def _lit(self, v: Any) -> str:
        if v is None:
            return "NULL"
        if isinstance(v, (int, float)):
            return str(v)
        return "'" + str(v).replace("'", "''") + "'"
