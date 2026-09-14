"""pdf_parser 标题抽取回归测试：避免把前言套话当成标准名称。"""

from utils.pdf_parser import pdf_parser


SAMPLE = """ICS07060
.
A47
中 华 人 民 共 和 国 国 家 标 准
GB/T31709—2015
气相色谱法本底大气二氧化碳和
甲烷浓度在线观测数据处理方法
Dataprocessingofbackgroundatmosphericcarbondioxideandmethane
concentrationmeasuredbyinsitugaschromatographic GC system
( )
2015-06-02发布 2016-01-01实施
中华人民共和国国家质量监督检验检疫总局
发 布
中 国 国 家 标 准 化 管 理 委 员 会
GB/T31709—2015
前 言
本标准按照 给出的规则起草
GB/T1.1—2009 。
本标准由中国气象局提出
。
1 范围
本标准规定了气相色谱法本底大气二氧化碳和甲烷浓度在线观测数据的处理方法。
"""


class TestPdfParserTitle:
    def test_prefers_cover_title_over_preface(self) -> None:
        records = pdf_parser.parse_text(
            SAMPLE,
            source_name="气相色谱法本底大气二氧化碳和甲烷浓度在线观测数据处理方法.pdf",
        )
        assert records
        assert records[0]["standard_no"].replace(" ", "") == "GB/T31709-2015"
        assert records[0]["name"] == "气相色谱法本底大气二氧化碳和甲烷浓度在线观测数据处理方法"
        assert "给出的规则起草" not in records[0]["name"]
        assert not records[0]["name"].startswith("本标准")

    def test_filename_fallback_when_needed(self) -> None:
        title = pdf_parser._title_from_source_name(
            "20260706_174935_科技平台 元数据汇交业务流程.pdf"
        )
        assert title == "科技平台元数据汇交业务流程"
