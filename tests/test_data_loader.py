import pandas as pd

from core.data_loader import detect_column_types, parse_pasted_text, to_number


def test_parse_pasted_text_tab_separated():
    text = "年\t件数\n2020\t120\n2021\t145"
    df = parse_pasted_text(text)
    assert list(df.columns) == ["年", "件数"]
    assert len(df) == 2


def test_parse_pasted_text_comma_separated():
    text = "企業,件数\nA社,10\nB社,20"
    df = parse_pasted_text(text)
    assert list(df.columns) == ["企業", "件数"]
    assert len(df) == 2


def test_parse_pasted_text_without_header():
    text = "2020\t120\n2021\t145"
    df = parse_pasted_text(text)
    assert list(df.columns) == ["列1", "列2"]
    assert len(df) == 2


def test_to_number_handles_comma_and_zenkaku():
    assert to_number("1,234") == 1234.0
    assert to_number("１２３") == 123.0
    assert to_number("") is None
    assert to_number("abc") is None


def test_detect_column_types():
    df = pd.DataFrame(
        {
            "年": ["2020", "2021"],
            "企業": ["A社", "B社"],
            "件数": ["10", "1,200"],
        }
    )
    types = detect_column_types(df)
    assert types["年"] == "年"
    assert types["企業"] == "文字"
    assert types["件数"] == "数値"


SALES_TEXT = (
    "\t2017\t2018\t2019\n"
    "連結売上高(億円)\t3,208.20\t3,284.10\t3,377.90\n"
    "営業利益(億円)\t67.1\t12\t7.4"
)


def test_row_series_table_is_detected_and_transposed():
    from core.data_loader import is_row_series, rows_to_series

    df = parse_pasted_text(SALES_TEXT)
    assert is_row_series(df)
    out = rows_to_series(df)
    assert list(out.columns) == ["年", "連結売上高(億円)", "営業利益(億円)"]
    assert out["年"].tolist() == ["2017", "2018", "2019"]
    assert to_number(out["連結売上高(億円)"][0]) == 3208.2
    assert detect_column_types(out)["年"] == "年"


def test_column_series_table_is_not_transposed():
    from core.data_loader import is_row_series

    df = parse_pasted_text("年\t件数\t累積件数\n2020\t120\t120\n2021\t145\t265")
    assert not is_row_series(df)
