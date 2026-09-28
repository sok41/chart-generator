"""スプレッドシートの貼り付けデータやファイルを読み込み、型判定を行うモジュール。"""
from __future__ import annotations

import io
import re
import unicodedata
from dataclasses import dataclass, field

import pandas as pd

YEAR_MIN = 1900
YEAR_MAX = 2100


@dataclass
class LoadResult:
    df: pd.DataFrame
    column_types: dict[str, str]
    warnings: list[str] = field(default_factory=list)


def _normalize_cell(value):
    if not isinstance(value, str):
        return value
    return unicodedata.normalize("NFKC", value).strip()


def parse_pasted_text(text: str) -> pd.DataFrame:
    """タブ区切り(スプレッドシートのコピー)またはカンマ区切りのテキストをDataFrameへ変換する。"""
    text = text.strip("\n")
    if not text.strip():
        return pd.DataFrame()

    first_line = text.splitlines()[0]
    delimiter = "\t" if "\t" in first_line else ","

    raw = pd.read_csv(
        io.StringIO(text), sep=delimiter, header=None, dtype=str, keep_default_na=False
    )
    return _finalize_header(raw)


def load_uploaded_file(uploaded_file) -> pd.DataFrame:
    """CSV / XLSX ファイルを読み込む。"""
    name = uploaded_file.name.lower()
    if name.endswith(".xlsx") or name.endswith(".xls"):
        raw = pd.read_excel(uploaded_file, header=None, dtype=str)
        raw = raw.fillna("")
    else:
        raw = pd.read_csv(uploaded_file, header=None, dtype=str, keep_default_na=False)
    return _finalize_header(raw)


def _looks_numeric(value) -> bool:
    if value is None:
        return False
    text = _normalize_cell(str(value))
    if text == "":
        return False
    text = text.replace(",", "")
    try:
        float(text)
        return True
    except ValueError:
        return False


def _finalize_header(raw: pd.DataFrame) -> pd.DataFrame:
    raw = raw.apply(lambda col: col.map(_normalize_cell))
    first_row = raw.iloc[0].tolist() if len(raw) else []
    has_header = not (first_row and all(_looks_numeric(v) for v in first_row))

    if has_header:
        columns = [c if c else f"列{i + 1}" for i, c in enumerate(first_row)]
        df = raw.iloc[1:].reset_index(drop=True)
        df.columns = columns
    else:
        df = raw.reset_index(drop=True)
        df.columns = [f"列{i + 1}" for i in range(df.shape[1])]

    return df


def is_row_series(df: pd.DataFrame) -> bool:
    """1行が1系列の表(列見出しが年・数値で、1列目が系列名)かどうかを判定する。"""
    if df.empty or df.shape[1] < 3:
        return False
    if not all(_looks_numeric(h) for h in df.columns[1:]):
        return False
    return not df.iloc[:, 0].map(_looks_numeric).all()


def rows_to_series(df: pd.DataFrame) -> pd.DataFrame:
    """1行が1系列の表を、1列が1系列の表へ入れ替える(1列目の値が系列名になる)。"""
    first_col = str(df.columns[0])
    if re.fullmatch(r"列\d+", first_col):
        headers = pd.Series(df.columns[1:])
        first_col = "年" if _looks_year(headers) else "項目"

    names: list[str] = []
    for i, value in enumerate(df.iloc[:, 0].astype(str)):
        name = value.strip() or f"系列{i + 1}"
        base, n = name, 2
        while name in names or name == first_col:
            name = f"{base}({n})"
            n += 1
        names.append(name)

    body = df.iloc[:, 1:]
    out = pd.DataFrame(body.to_numpy().T, columns=names)
    out.insert(0, first_col, [str(c) for c in body.columns])
    return out


def to_number(value):
    """カンマ区切り・全角数字を含む文字列を数値に変換する。変換できない場合はNoneを返す。"""
    if value is None:
        return None
    text = _normalize_cell(str(value)).replace(",", "")
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _looks_year(series: pd.Series) -> bool:
    numbers = series.map(to_number).dropna()
    if numbers.empty:
        return False
    return bool(((numbers >= YEAR_MIN) & (numbers <= YEAR_MAX) & (numbers == numbers.round())).all())


def detect_column_types(df: pd.DataFrame) -> dict[str, str]:
    """列ごとに「数値」「年」「文字」を自動判定する。"""
    types: dict[str, str] = {}
    for col in df.columns:
        series = df[col].astype(str)
        non_empty = series[series.str.strip() != ""]
        if non_empty.empty:
            types[col] = "文字"
            continue
        numeric_ratio = non_empty.map(_looks_numeric).mean()
        if numeric_ratio == 1.0:
            types[col] = "年" if _looks_year(non_empty) else "数値"
        else:
            types[col] = "文字"
    return types


def build_warnings(df: pd.DataFrame, column_types: dict[str, str]) -> list[str]:
    """空欄や数値へ変換できないセルについての警告メッセージを作成する。"""
    warnings: list[str] = []
    for col in df.columns:
        series = df[col].astype(str)
        empty_count = int((series.str.strip() == "").sum())
        if empty_count:
            warnings.append(f"列「{col}」に空欄が{empty_count}件あります。")

        if column_types.get(col) in ("数値", "年"):
            filled = series[series.str.strip() != ""]
            bad_count = int(filled.map(lambda v: to_number(v) is None).sum())
            if bad_count:
                warnings.append(f"列「{col}」に数値へ変換できないセルが{bad_count}件あります。")
    return warnings


def load_result_from_dataframe(df: pd.DataFrame) -> LoadResult:
    column_types = detect_column_types(df)
    warnings = build_warnings(df, column_types)
    return LoadResult(df=df, column_types=column_types, warnings=warnings)


def numeric_series(df: pd.DataFrame, col: str) -> pd.Series:
    """指定した列を数値(float)のSeriesへ変換する。"""
    return df[col].map(to_number)
