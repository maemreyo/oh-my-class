"""#465 (Content Intelligence Graph): a small, honestly-scoped CCSS Math sample.

**What this is**: 5 real CCSS Math standard codes (verified against the
publicly published Common Core State Standards for Mathematics, NGA Center
for Best Practices & CCSSO, 2010, https://corestandards.org -- reproduction
of standard codes/text permitted for non-commercial educational use under the
CCSS Public License), each wired to one knowledge component through a
`CurriculumAlignmentRecord`, plus a small illustrative `PrerequisiteGraph`
showing how those five knowledge components sequence across grades 3-7.

**What this is NOT**: a certified or complete catalog. It is 5 records,
covers one framework (CCSS Math) out of three the issue names (MOET 2018,
CCSS, NGSS), and the prerequisite *sequencing* between them (e.g. "ratio
understanding before variables/equations") is this author's reasonable,
reviewed pedagogical judgment, not itself a claim sourced from the CCSS
document (the CCSS text does not itself assert cross-standard prerequisite
edges). MOET 2018 and NGSS remain unseeded: this session did not have
reliable, checkable source text for either, and fabricating codes or
Vietnamese-curriculum claims would be worse than leaving them as an explicit
TODO. Real seeding of either -- or of the rest of CCSS Math -- is future,
separate, reviewed content work.
"""

from __future__ import annotations

from common.contracts.claim_evidence import ClaimEvidence
from common.contracts.content_intelligence_graph.alignment import CurriculumAlignmentRecord
from common.contracts.content_intelligence_graph.prerequisite import PrerequisiteGraph, PrerequisiteNode
from common.contracts.content_intelligence_graph.snapshot import compute_snapshot_version
from common.contracts.subject_capability_pack import CurriculumStandard

_CCSS_MATH_CITATION = (
    "Common Core State Standards for Mathematics, NGA Center for Best Practices "
    "& Council of Chief State School Officers, 2010 -- https://corestandards.org/math/"
)

SCOPE = "ccss_math_sample"

_KNOWLEDGE_COMPONENTS: tuple[PrerequisiteNode, ...] = (
    PrerequisiteNode(
        node_id="kc.ccss_math_sample.3.oa.a.1",
        description="Interpret products of whole numbers as groups of objects (e.g. 5 x 7 as 5 groups of 7).",
        scope=SCOPE,
        requires=(),
    ),
    PrerequisiteNode(
        node_id="kc.ccss_math_sample.4.nbt.b.5",
        description="Multiply multi-digit whole numbers using place-value strategies and properties of operations.",
        scope=SCOPE,
        requires=("kc.ccss_math_sample.3.oa.a.1",),
    ),
    PrerequisiteNode(
        node_id="kc.ccss_math_sample.5.nf.b.4",
        description="Multiply a fraction or whole number by a fraction.",
        scope=SCOPE,
        requires=("kc.ccss_math_sample.4.nbt.b.5",),
    ),
    PrerequisiteNode(
        node_id="kc.ccss_math_sample.6.rp.a.1",
        description="Understand the concept of a ratio and use ratio language to describe a ratio relationship.",
        scope=SCOPE,
        requires=("kc.ccss_math_sample.5.nf.b.4",),
    ),
    PrerequisiteNode(
        node_id="kc.ccss_math_sample.7.ee.b.4",
        description="Use variables to represent quantities and construct simple equations/inequalities to solve problems.",
        scope=SCOPE,
        requires=("kc.ccss_math_sample.6.rp.a.1",),
    ),
)

CCSS_MATH_SAMPLE_PREREQUISITE_GRAPH = PrerequisiteGraph(
    snapshot_version=compute_snapshot_version(_KNOWLEDGE_COMPONENTS, prefix="ccss-math-sample"),
    nodes=_KNOWLEDGE_COMPONENTS,
)

CCSS_MATH_SAMPLE_ALIGNMENTS: tuple[CurriculumAlignmentRecord, ...] = (
    CurriculumAlignmentRecord(
        knowledge_component_id="kc.ccss_math_sample.3.oa.a.1",
        standard=CurriculumStandard(
            framework="CCSS",
            code="CCSS.MATH.CONTENT.3.OA.A.1",
            description_en=(
                "Interpret products of whole numbers, e.g., interpret 5 x 7 as the total number "
                "of objects in 5 groups of 7 objects each."
            ),
            description_vi=(
                "Diễn giải tích của các số tự nhiên, ví dụ: diễn giải 5 x 7 là tổng số đồ vật "
                "trong 5 nhóm, mỗi nhóm có 7 đồ vật."
            ),
        ),
        evidence=ClaimEvidence(
            claim_id="alignment.ccss_math_sample.3.oa.a.1",
            claim_text=_CCSS_MATH_CITATION,
            risk_level="medium",
            citation_ids=["corestandards.org/math/content/3/OA/"],
            verification_status="VERIFIED",
        ),
    ),
    CurriculumAlignmentRecord(
        knowledge_component_id="kc.ccss_math_sample.4.nbt.b.5",
        standard=CurriculumStandard(
            framework="CCSS",
            code="CCSS.MATH.CONTENT.4.NBT.B.5",
            description_en=(
                "Multiply a whole number of up to four digits by a one-digit whole number, and "
                "multiply two two-digit numbers, using strategies based on place value and the "
                "properties of operations."
            ),
            description_vi=(
                "Nhân một số tự nhiên có tối đa bốn chữ số với một số tự nhiên có một chữ số, và "
                "nhân hai số có hai chữ số, sử dụng các chiến lược dựa trên giá trị theo vị trí và "
                "các tính chất của phép tính."
            ),
        ),
        evidence=ClaimEvidence(
            claim_id="alignment.ccss_math_sample.4.nbt.b.5",
            claim_text=_CCSS_MATH_CITATION,
            risk_level="medium",
            citation_ids=["corestandards.org/math/content/4/NBT/"],
            verification_status="VERIFIED",
        ),
    ),
    CurriculumAlignmentRecord(
        knowledge_component_id="kc.ccss_math_sample.5.nf.b.4",
        standard=CurriculumStandard(
            framework="CCSS",
            code="CCSS.MATH.CONTENT.5.NF.B.4",
            description_en=(
                "Apply and extend previous understandings of multiplication to multiply a "
                "fraction or whole number by a fraction."
            ),
            description_vi=(
                "Áp dụng và mở rộng hiểu biết trước đây về phép nhân để nhân một phân số hoặc "
                "số tự nhiên với một phân số."
            ),
        ),
        evidence=ClaimEvidence(
            claim_id="alignment.ccss_math_sample.5.nf.b.4",
            claim_text=_CCSS_MATH_CITATION,
            risk_level="medium",
            citation_ids=["corestandards.org/math/content/5/NF/"],
            verification_status="VERIFIED",
        ),
    ),
    CurriculumAlignmentRecord(
        knowledge_component_id="kc.ccss_math_sample.6.rp.a.1",
        standard=CurriculumStandard(
            framework="CCSS",
            code="CCSS.MATH.CONTENT.6.RP.A.1",
            description_en=(
                "Understand the concept of a ratio and use ratio language to describe a ratio "
                "relationship between two quantities."
            ),
            description_vi=(
                "Hiểu khái niệm tỉ số và sử dụng ngôn ngữ tỉ số để mô tả mối quan hệ tỉ số giữa "
                "hai đại lượng."
            ),
        ),
        evidence=ClaimEvidence(
            claim_id="alignment.ccss_math_sample.6.rp.a.1",
            claim_text=_CCSS_MATH_CITATION,
            risk_level="medium",
            citation_ids=["corestandards.org/math/content/6/RP/"],
            verification_status="VERIFIED",
        ),
    ),
    CurriculumAlignmentRecord(
        knowledge_component_id="kc.ccss_math_sample.7.ee.b.4",
        standard=CurriculumStandard(
            framework="CCSS",
            code="CCSS.MATH.CONTENT.7.EE.B.4",
            description_en=(
                "Use variables to represent quantities in a real-world or mathematical problem, "
                "and construct simple equations and inequalities to solve problems by reasoning "
                "about the quantities."
            ),
            description_vi=(
                "Sử dụng biến số để biểu diễn các đại lượng trong một bài toán thực tế hoặc toán "
                "học, và xây dựng các phương trình và bất phương trình đơn giản để giải quyết vấn "
                "đề bằng cách suy luận về các đại lượng."
            ),
        ),
        evidence=ClaimEvidence(
            claim_id="alignment.ccss_math_sample.7.ee.b.4",
            claim_text=_CCSS_MATH_CITATION,
            risk_level="medium",
            citation_ids=["corestandards.org/math/content/7/EE/"],
            verification_status="VERIFIED",
        ),
    ),
)
