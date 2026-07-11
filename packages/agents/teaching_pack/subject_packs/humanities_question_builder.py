"""Real, declared-answer Humanities and Social Studies question generation
per Grade Band (#450).

Bridges the Humanities Subject Capability Pack's declared misconceptions
(common/component_strategy_knowledge/capabilities/humanities_capability_pack.json)
to actual quiz/drill content, reusing the declared-answer `FixedAnswerQuestion`
shape #449 introduced for non-arithmetic subjects (civics, geography, history,
and literature theme analysis aren't solver-checkable the way Math/Science
are). One overlay domain is covered per Grade Band -- civics (K-2), geography
/ map reading (3-5), history / primary vs secondary sourcing (6-8), and
literature / theme vs plot (9-12) -- mirroring how #447/#448 covered one
concept per band rather than every domain at every band.

Every item is authored bilingually (English and Vietnamese content, not a
machine translation at runtime); `target_language` is accepted for signature
parity with subject builders that need it (#449) but unused here -- these
overlays aren't about which language is being taught, just which locale the
content is rendered in.
"""

from __future__ import annotations

import random
from collections.abc import Callable

from common.contracts.grade_band import GradeBand
from packages.agents.teaching_pack.subject_packs.fixed_answer_question_builder import (
    FixedAnswerQuestion,
    build_fixed_answer_question,
)

_STANDARD_CODE_BY_BAND: dict[GradeBand, str] = {
    GradeBand.K_2: "MOET.DAODUC.1.NOI_QUY",
    GradeBand.GRADES_3_5: "MOET.DIALY.5.BAN_DO",
    GradeBand.GRADES_6_8: "MOET.LICHSU.8.NGUON_SU_LIEU",
    GradeBand.GRADES_9_12: "MOET.NGUVAN.11.CHU_DE_TAC_PHAM",
}

_MISCONCEPTION_ID_BY_BAND: dict[GradeBand, str] = {
    GradeBand.K_2: "k2_thinks_rules_exist_only_to_punish",
    GradeBand.GRADES_3_5: "grade35_confuses_map_up_with_forward_direction",
    GradeBand.GRADES_6_8: "grade68_assumes_old_document_is_always_primary_source",
    GradeBand.GRADES_9_12: "grade912_confuses_plot_summary_with_theme",
}

# -- K-2: civics -- why a classroom/school rule exists ----------------------

_CIVICS_ITEMS: list[dict[str, str]] = [
    {
        "prompt_en": 'Why does the classroom have a rule to "raise your hand before speaking"?',
        "prompt_vi": 'Vì sao lớp học có nội quy "giơ tay trước khi phát biểu"?',
        "correct_en": "So everyone gets a fair turn to speak and no one talks over each other.",
        "correct_vi": "Để mọi người đều có lượt phát biểu công bằng và không ai nói chen ngang.",
        "misconception_en": "So the teacher can punish students who forget.",
        "misconception_vi": "Để giáo viên có thể phạt học sinh nào quên giơ tay.",
        "distractor_a_en": "So the classroom looks tidy.",
        "distractor_a_vi": "Để lớp học trông gọn gàng hơn.",
        "distractor_b_en": "So only the teacher is allowed to talk.",
        "distractor_b_vi": "Để chỉ có giáo viên được phép nói.",
    },
    {
        "prompt_en": 'Why does the school have a rule to "walk, don\'t run, in the hallway"?',
        "prompt_vi": 'Vì sao trường có nội quy "đi bộ, không chạy trong hành lang"?',
        "correct_en": "So no one gets hurt by bumping into someone else.",
        "correct_vi": "Để không ai bị va chạm và bị thương.",
        "misconception_en": "So the teacher can send you to the office.",
        "misconception_vi": "Để giáo viên có thể gửi bạn lên phòng hiệu trưởng.",
        "distractor_a_en": "So hallways stay quiet.",
        "distractor_a_vi": "Để hành lang luôn yên tĩnh.",
        "distractor_b_en": "So the floor doesn't get dirty.",
        "distractor_b_vi": "Để sàn nhà không bị bẩn.",
    },
    {
        "prompt_en": 'Why does the classroom have a rule to "put toys away after playtime"?',
        "prompt_vi": 'Vì sao lớp học có nội quy "cất đồ chơi sau giờ chơi"?',
        "correct_en": "So everyone can find toys again and the room stays safe to walk in.",
        "correct_vi": "Để mọi người dễ tìm lại đồ chơi và phòng học vẫn an toàn để đi lại.",
        "misconception_en": "So you get a prize for being neat.",
        "misconception_vi": "Để được thưởng vì gọn gàng.",
        "distractor_a_en": "So toys never break.",
        "distractor_a_vi": "Để đồ chơi không bao giờ hỏng.",
        "distractor_b_en": "So the teacher doesn't have to clean.",
        "distractor_b_vi": "Để giáo viên không phải dọn dẹp.",
    },
]

# -- Grades 3-5: geography -- reading a compass rose, not just page position

_MAP_ITEMS: list[dict[str, str]] = [
    {
        "prompt_en": "This map's compass rose points North toward the bottom of the page. The bridge is drawn below the town square. Which direction is the bridge from the town square?",
        "prompt_vi": "La bàn trên bản đồ này chỉ hướng Bắc về phía dưới trang. Cây cầu được vẽ ở phía dưới quảng trường thị trấn. Cây cầu ở hướng nào so với quảng trường?",
        "correct_en": "North", "correct_vi": "Hướng Bắc",
        "misconception_en": "South", "misconception_vi": "Hướng Nam",
        "distractor_a_en": "East", "distractor_a_vi": "Hướng Đông",
        "distractor_b_en": "West", "distractor_b_vi": "Hướng Tây",
    },
    {
        "prompt_en": "This map's compass rose points North toward the right side of the page. The farm is drawn to the right of the well. Which direction is the farm from the well?",
        "prompt_vi": "La bàn trên bản đồ này chỉ hướng Bắc về phía bên phải trang. Nông trại được vẽ ở bên phải giếng nước. Nông trại ở hướng nào so với giếng nước?",
        "correct_en": "North", "correct_vi": "Hướng Bắc",
        "misconception_en": "East", "misconception_vi": "Hướng Đông",
        "distractor_a_en": "South", "distractor_a_vi": "Hướng Nam",
        "distractor_b_en": "West", "distractor_b_vi": "Hướng Tây",
    },
    {
        "prompt_en": "This map's compass rose points North toward the left side of the page. The garden is drawn to the left of the house. Which direction is the garden from the house?",
        "prompt_vi": "La bàn trên bản đồ này chỉ hướng Bắc về phía bên trái trang. Khu vườn được vẽ ở bên trái ngôi nhà. Khu vườn ở hướng nào so với ngôi nhà?",
        "correct_en": "North", "correct_vi": "Hướng Bắc",
        "misconception_en": "West", "misconception_vi": "Hướng Tây",
        "distractor_a_en": "South", "distractor_a_vi": "Hướng Nam",
        "distractor_b_en": "East", "distractor_b_vi": "Hướng Đông",
    },
]

# -- Grades 6-8: history -- primary vs secondary source, by authorship, not age

_SOURCE_ITEMS: list[dict[str, str]] = [
    {
        "prompt_en": "A soldier wrote a letter to his family the night after a battle he fought in. A historian later summarized that battle in a textbook 100 years afterward. Which one is the primary source?",
        "prompt_vi": "Một người lính viết thư cho gia đình ngay đêm sau trận đánh anh ta đã tham gia. Một nhà sử học sau đó tóm tắt trận đánh đó trong sách giáo khoa 100 năm sau. Đâu là tư liệu gốc (sơ cấp)?",
        "correct_en": "The soldier's letter.", "correct_vi": "Bức thư của người lính.",
        "misconception_en": "The textbook, because it looks more official and complete.",
        "misconception_vi": "Sách giáo khoa, vì trông chính thống và đầy đủ hơn.",
        "distractor_a_en": "Neither -- only physical artifacts count as primary sources.",
        "distractor_a_vi": "Không cái nào -- chỉ hiện vật mới được coi là tư liệu gốc.",
        "distractor_b_en": "Both are equally primary sources.",
        "distractor_b_vi": "Cả hai đều là tư liệu gốc như nhau.",
    },
    {
        "prompt_en": "A newspaper reporter interviewed eyewitnesses right after a fire and published the article the next day. Decades later, a documentary filmmaker used old records to reconstruct the event. Which is the primary source?",
        "prompt_vi": "Một phóng viên phỏng vấn nhân chứng ngay sau vụ hỏa hoạn và đăng bài hôm sau. Nhiều thập kỷ sau, một nhà làm phim tài liệu dùng hồ sơ cũ để dựng lại sự kiện. Đâu là tư liệu gốc (sơ cấp)?",
        "correct_en": "The newspaper article written right after the event.",
        "correct_vi": "Bài báo được viết ngay sau sự kiện.",
        "misconception_en": "The documentary, because it is more recent and detailed.",
        "misconception_vi": "Phim tài liệu, vì mới hơn và chi tiết hơn.",
        "distractor_a_en": "Neither is a primary source.",
        "distractor_a_vi": "Không cái nào là tư liệu gốc.",
        "distractor_b_en": "Both are secondary sources.",
        "distractor_b_vi": "Cả hai đều là tư liệu thứ cấp.",
    },
    {
        "prompt_en": "A diary entry was written by a factory worker during a historic strike. A history textbook chapter about the strike was published 50 years later. Which is the primary source?",
        "prompt_vi": "Một trang nhật ký được viết bởi một công nhân nhà máy trong cuộc đình công lịch sử. Một chương sách lịch sử về cuộc đình công đó được xuất bản 50 năm sau. Đâu là tư liệu gốc (sơ cấp)?",
        "correct_en": "The diary entry.", "correct_vi": "Trang nhật ký.",
        "misconception_en": "The textbook, because it was written by an expert.",
        "misconception_vi": "Sách giáo khoa, vì do chuyên gia viết.",
        "distractor_a_en": "Neither -- diaries are considered secondary sources.",
        "distractor_a_vi": "Không cái nào -- nhật ký được coi là tư liệu thứ cấp.",
        "distractor_b_en": "Both are primary sources.",
        "distractor_b_vi": "Cả hai đều là tư liệu gốc.",
    },
]

# -- Grades 9-12: literature -- theme (message) vs plot (events) -----------

_THEME_ITEMS: list[dict[str, str]] = [
    {
        "prompt_en": (
            "A young girl leaves her village to find work in the city, faces hardship, and eventually "
            "returns home wiser and closer to her family. What is the THEME of this story (not a plot summary)?"
        ),
        "prompt_vi": (
            "Một cô gái trẻ rời làng đi tìm việc ở thành phố, trải qua khó khăn, rồi trở về nhà khôn ngoan hơn "
            "và gần gũi hơn với gia đình. CHỦ ĐỀ của câu chuyện này là gì (không phải tóm tắt cốt truyện)?"
        ),
        "correct_en": "Personal growth often comes through hardship and leads to a deeper appreciation of home and family.",
        "correct_vi": "Sự trưởng thành thường đến từ khó khăn và dẫn đến sự trân trọng sâu sắc hơn với gia đình.",
        "misconception_en": "A young girl leaves her village to find work in the city, faces hardship, and returns home.",
        "misconception_vi": "Một cô gái trẻ rời làng đi tìm việc ở thành phố, trải qua khó khăn, rồi trở về nhà.",
        "distractor_a_en": "The girl should never have left her village.",
        "distractor_a_vi": "Cô gái lẽ ra không nên rời làng.",
        "distractor_b_en": "City life is always harder than village life.",
        "distractor_b_vi": "Cuộc sống thành phố luôn khó khăn hơn ở làng quê.",
    },
    {
        "prompt_en": (
            "A soldier returns from war unable to relate to his old friends, and slowly rebuilds trust with his "
            "family over several years. What is the THEME of this story (not a plot summary)?"
        ),
        "prompt_vi": (
            "Một người lính trở về sau chiến tranh không thể hòa nhập với bạn bè cũ, và dần lấy lại niềm tin với "
            "gia đình qua nhiều năm. CHỦ ĐỀ của câu chuyện này là gì (không phải tóm tắt cốt truyện)?"
        ),
        "correct_en": "Recovering from trauma and reconnecting with loved ones takes time and patience.",
        "correct_vi": "Hồi phục sau tổn thương và gắn kết lại với người thân cần thời gian và sự kiên nhẫn.",
        "misconception_en": "A soldier returns from war unable to relate to his old friends and rebuilds trust with his family.",
        "misconception_vi": "Một người lính trở về sau chiến tranh không hòa nhập được với bạn cũ và lấy lại niềm tin với gia đình.",
        "distractor_a_en": "War changes people for the worse forever.",
        "distractor_a_vi": "Chiến tranh luôn thay đổi con người theo hướng xấu mãi mãi.",
        "distractor_b_en": "Soldiers should avoid contact with family after war.",
        "distractor_b_vi": "Người lính nên tránh tiếp xúc với gia đình sau chiến tranh.",
    },
    {
        "prompt_en": (
            "Two rival merchants compete for years until they realize that working together makes both of "
            "their businesses stronger. What is the THEME of this story (not a plot summary)?"
        ),
        "prompt_vi": (
            "Hai thương nhân đối thủ cạnh tranh nhiều năm cho đến khi họ nhận ra hợp tác giúp cả hai việc kinh "
            "doanh đều vững mạnh hơn. CHỦ ĐỀ của câu chuyện này là gì (không phải tóm tắt cốt truyện)?"
        ),
        "correct_en": "Cooperation can achieve more than competition alone.",
        "correct_vi": "Hợp tác có thể đạt được nhiều hơn là chỉ cạnh tranh đơn thuần.",
        "misconception_en": "Two rival merchants compete for years until they realize working together makes both businesses stronger.",
        "misconception_vi": "Hai thương nhân đối thủ cạnh tranh nhiều năm cho đến khi nhận ra hợp tác giúp cả hai vững mạnh hơn.",
        "distractor_a_en": "Merchants should always avoid rivals.",
        "distractor_a_vi": "Thương nhân nên luôn tránh đối thủ cạnh tranh.",
        "distractor_b_en": "Only one business can succeed at a time.",
        "distractor_b_vi": "Chỉ một việc kinh doanh có thể thành công tại một thời điểm.",
    },
]


def _item_to_question(
    item: dict[str, str], *, id_prefix: str, index: int, grade_band: GradeBand, standard_code: str, misconception_id: str,
) -> FixedAnswerQuestion:
    return build_fixed_answer_question(
        id_prefix=id_prefix, index=index, grade_band=grade_band,
        standard_code=standard_code, misconception_id=misconception_id,
        prompt_en=item["prompt_en"], prompt_vi=item["prompt_vi"],
        correct_en=item["correct_en"], correct_vi=item["correct_vi"],
        misconception_en=item["misconception_en"], misconception_vi=item["misconception_vi"],
        distractor_a_en=item["distractor_a_en"], distractor_a_vi=item["distractor_a_vi"],
        distractor_b_en=item["distractor_b_en"], distractor_b_vi=item["distractor_b_vi"],
        explain_en=f'"{item["correct_en"]}" is correct; "{item["misconception_en"]}" is a documented misconception, not the answer.',
        explain_vi=f'"{item["correct_vi"]}" là đáp án đúng; "{item["misconception_vi"]}" là ngộ nhận thường gặp, không phải đáp án.',
    )


def _k2_question(rng: random.Random, index: int) -> FixedAnswerQuestion:
    del rng
    item = _CIVICS_ITEMS[index % len(_CIVICS_ITEMS)]
    return _item_to_question(
        item, id_prefix="humanities", index=index, grade_band=GradeBand.K_2,
        standard_code=_STANDARD_CODE_BY_BAND[GradeBand.K_2],
        misconception_id=_MISCONCEPTION_ID_BY_BAND[GradeBand.K_2],
    )


def _grade35_question(rng: random.Random, index: int) -> FixedAnswerQuestion:
    del rng
    item = _MAP_ITEMS[index % len(_MAP_ITEMS)]
    return _item_to_question(
        item, id_prefix="humanities", index=index, grade_band=GradeBand.GRADES_3_5,
        standard_code=_STANDARD_CODE_BY_BAND[GradeBand.GRADES_3_5],
        misconception_id=_MISCONCEPTION_ID_BY_BAND[GradeBand.GRADES_3_5],
    )


def _grade68_question(rng: random.Random, index: int) -> FixedAnswerQuestion:
    del rng
    item = _SOURCE_ITEMS[index % len(_SOURCE_ITEMS)]
    return _item_to_question(
        item, id_prefix="humanities", index=index, grade_band=GradeBand.GRADES_6_8,
        standard_code=_STANDARD_CODE_BY_BAND[GradeBand.GRADES_6_8],
        misconception_id=_MISCONCEPTION_ID_BY_BAND[GradeBand.GRADES_6_8],
    )


def _grade912_question(rng: random.Random, index: int) -> FixedAnswerQuestion:
    del rng
    item = _THEME_ITEMS[index % len(_THEME_ITEMS)]
    return _item_to_question(
        item, id_prefix="humanities", index=index, grade_band=GradeBand.GRADES_9_12,
        standard_code=_STANDARD_CODE_BY_BAND[GradeBand.GRADES_9_12],
        misconception_id=_MISCONCEPTION_ID_BY_BAND[GradeBand.GRADES_9_12],
    )


_GENERATORS: dict[GradeBand, Callable[[random.Random, int], FixedAnswerQuestion]] = {
    GradeBand.K_2: _k2_question,
    GradeBand.GRADES_3_5: _grade35_question,
    GradeBand.GRADES_6_8: _grade68_question,
    GradeBand.GRADES_9_12: _grade912_question,
}


def build_humanities_questions(
    grade_band: GradeBand, *, count: int = 4, seed: int = 0, target_language: str = "en",
) -> list[FixedAnswerQuestion]:
    """Deterministic given the same `seed` -- same grade band + seed always
    produces the same problem set (mirrors #447/#448's deterministic-and-
    traceable requirement). `target_language` is unused (see module docstring)."""
    del target_language
    rng = random.Random(seed)
    generator = _GENERATORS[grade_band]
    return [generator(rng, index) for index in range(count)]
