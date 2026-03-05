from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class Series(BaseModel):
    """Define una única serie de datos que se representará en el gráfico."""

    name: str = Field(..., description="Nombre de la serie (ej: 'Ventas Actuales').")
    data: List[float] = Field(
        ...,
        description="Valores numéricos de la serie. La longitud debe coincidir con 'labels'.",
    )
    color: Optional[str] = Field(
        None, description="Color opcional para la serie (ej: '#FF5733' o 'blue')."
    )


class EncodingAxis(BaseModel):
    """Define las propiedades de codificación y formato para un eje (X o Y) en el gráfico."""

    type: Literal["temporal", "nominal", "ordinal", "quantitative"] = Field(
        ...,
        description=(
            "Tipo de datos en el eje: 'temporal' (fechas/tiempo), 'nominal' (categorías sin orden), "
            "'ordinal' (categorías con orden) o 'quantitative' (valores numéricos)."
        ),
    )
    format: Optional[str] = Field(
        None,
        description="Formato específico para mostrar los valores (ej: '%Y-%m-%d' para fechas, '$,.2f' para moneda).",
    )
    unit: Optional[str] = Field(
        None, description="Unidad de medida para el eje Y (ej: 'USD', '%', 'miles')."
    )


class ChartSpec(BaseModel):
    """
    Especificación completa para construir un gráfico.
    Esta estructura combina metadatos del gráfico (tipo, codificación) con los datos puros (labels, series).
    """

    type: Optional[Literal["bar", "line", "pie"]] = Field(
        None, description="Tipo de gráfico sugerido (valor obsoleto, usar 'mark')."
    )
    mark: Optional[Literal["bar", "line", "area", "pie"]] = Field(
        None,
        description="Tipo de marca visual a usar para representar los datos (ej: 'line', 'bar').",
    )
    encoding: Optional[Dict[str, EncodingAxis]] = Field(
        None,
        description="Define las propiedades de codificación para los ejes. Estructura esperada: `{ 'x': EncodingAxis, 'y': EncodingAxis }`.",
    )

    title: Optional[str] = Field(None, description="Título principal del gráfico.")
    labels: List[str] = Field(
        ...,
        description="Etiquetas de la categoría o dimensión (eje X) que serán compartidas por todas las series.",
    )
    series: List[Series] = Field(
        ...,
        description="Lista de series de datos a dibujar. Cada serie contiene su nombre y sus valores.",
    )
    meta: Optional[Dict[str, str]] = Field(
        None,
        description="Metadatos adicionales o configuraciones específicas no incluidas en el esquema principal.",
    )

    @model_validator(mode="after")
    def _validate_lengths(self) -> "ChartSpec":
        """Valida que todas las series tengan la misma longitud que la lista de labels."""
        if not self.labels:
            raise ValueError("labels no puede estar vacío")
        for s in self.series:
            if len(s.data) != len(self.labels):
                raise ValueError(
                    f"La serie '{s.name}' tiene longitud {len(s.data)} que no coincide con labels {len(self.labels)}"
                )
        return self

    @field_validator("series")
    @classmethod
    def _validate_series_not_empty(cls, v: List[Series]) -> List[Series]:
        """Valida que la lista de series no esté vacía."""
        if not v:
            raise ValueError("series no puede estar vacío")
        return v
