"""Real, declared-answer Language and Literacy question generation per Grade
Band (#449).

Bridges the Language and Literacy Subject Capability Pack's declared
misconceptions
(common/component_strategy_knowledge/capabilities/language_literacy_capability_pack.json)
to actual quiz/drill content. Unlike Math/Science (#447, #448), correctness
here isn't solver-verifiable arithmetic, so questions use the declared-answer
`FixedAnswerQuestion` shape (`fixed_answer_question_builder.py`) instead of
`SolverQuestion`.

`target_language` (the language of the content being taught -- "en" for
EFL/ESL phonics/vocabulary/grammar/reading, "vi" for Vietnamese literacy) is
kept strictly separate from the instruction locale used for the surrounding
prompt/explanation text (#449 AC: contracts and workspace must not conflate
the two). Content items (the word, sentence, or passage under test) are
picked once from the target-language-specific bank and rendered identically
regardless of instruction locale; only the instructional wrapper and
explanation vary between `_en`/`_vi`.
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
    GradeBand.K_2: "MOET.TIENGVIET.1.GHEP_VAN",
    GradeBand.GRADES_3_5: "MOET.TIENGVIET.5.NGHIA_TU",
    GradeBand.GRADES_6_8: "MOET.NGUVAN.7.LOAI_TU",
    GradeBand.GRADES_9_12: "MOET.NGUVAN.11.LUAN_DIEM_CHINH",
}

# One misconception id per (band, target_language) -- English phonics/
# grammar and Vietnamese phonics/grammar are genuinely different linguistic
# phenomena (rime vs vần, subject-verb agreement vs classifier words), so
# they're guarded as distinct declared misconceptions rather than shared.
_MISCONCEPTION_ID_BY_BAND: dict[GradeBand, dict[str, str]] = {
    GradeBand.K_2: {
        "en": "k2_matches_onset_instead_of_rime",
        "vi": "k2_matches_onset_instead_of_van",
    },
    GradeBand.GRADES_3_5: {
        "en": "grade35_selects_familiar_meaning_ignoring_context",
        "vi": "grade35_chon_nghia_quen_thuoc_bo_qua_ngu_canh",
    },
    GradeBand.GRADES_6_8: {
        "en": "grade68_agrees_with_first_subject_not_nearest",
        "vi": "grade68_overgeneralizes_con_as_default_classifier",
    },
    GradeBand.GRADES_9_12: {
        "en": "grade912_assumes_first_sentence_is_main_idea",
        "vi": "grade912_nham_cau_dau_doan_la_luan_diem_chinh",
    },
}


def _resolve_target_language(target_language: str) -> str:
    return "vi" if target_language.strip().lower() == "vi" else "en"


# -- K-2: rhyme (English rime / Vietnamese vần) family banks ----------------

_K2_RIME_FAMILIES_EN: list[dict[str, str]] = [
    {"target": "cat", "correct": "hat", "onset_distractor": "cup", "distractor_a": "dog", "distractor_b": "sun"},
    {"target": "sun", "correct": "fun", "onset_distractor": "sit", "distractor_a": "cat", "distractor_b": "pig"},
    {"target": "pig", "correct": "big", "onset_distractor": "pot", "distractor_a": "hat", "distractor_b": "fox"},
    {"target": "fox", "correct": "box", "onset_distractor": "fan", "distractor_a": "sun", "distractor_b": "pig"},
]

_K2_VAN_FAMILIES_VI: list[dict[str, str]] = [
    {"target": "bàn", "correct": "sàn", "onset_distractor": "bút", "distractor_a": "mèo", "distractor_b": "sách"},
    {"target": "mèo", "correct": "kẹo", "onset_distractor": "múa", "distractor_a": "bàn", "distractor_b": "sách"},
    {"target": "sách", "correct": "cách", "onset_distractor": "sen", "distractor_a": "bàn", "distractor_b": "mèo"},
    {"target": "gà", "correct": "cà", "onset_distractor": "ghế", "distractor_a": "mèo", "distractor_b": "sách"},
]


def _k2_question(rng: random.Random, index: int, target_language: str) -> FixedAnswerQuestion:
    resolved = _resolve_target_language(target_language)
    families = _K2_VAN_FAMILIES_VI if resolved == "vi" else _K2_RIME_FAMILIES_EN
    family = families[index % len(families)]
    target, correct, onset, distractor_a, distractor_b = (
        family["target"], family["correct"], family["onset_distractor"], family["distractor_a"], family["distractor_b"],
    )
    if resolved == "vi":
        prompt_en = f'Which word rhymes with "{target}" (same vần)?'
        prompt_vi = f'Từ nào cùng vần với "{target}"?'
        explain_en = f'"{correct}" shares the same vần as "{target}"; "{onset}" only shares the first consonant.'
        explain_vi = f'"{correct}" cùng vần với "{target}"; "{onset}" chỉ giống phụ âm đầu, không cùng vần.'
    else:
        prompt_en = f'Which word rhymes with "{target}"?'
        prompt_vi = f'Từ tiếng Anh nào vần với "{target}"?'
        explain_en = f'"{correct}" rhymes with "{target}" (same ending sound); "{onset}" only starts the same way.'
        explain_vi = f'"{correct}" vần với "{target}" (cùng âm cuối); "{onset}" chỉ giống âm đầu.'
    return build_fixed_answer_question(
        id_prefix="language_literacy", index=index, grade_band=GradeBand.K_2,
        standard_code=_STANDARD_CODE_BY_BAND[GradeBand.K_2],
        misconception_id=_MISCONCEPTION_ID_BY_BAND[GradeBand.K_2][resolved],
        prompt_en=prompt_en, prompt_vi=prompt_vi,
        correct_en=correct, correct_vi=correct,
        misconception_en=onset, misconception_vi=onset,
        distractor_a_en=distractor_a, distractor_a_vi=distractor_a,
        distractor_b_en=distractor_b, distractor_b_vi=distractor_b,
        explain_en=explain_en, explain_vi=explain_vi,
    )


# -- Grades 3-5: multiple-meaning word in context ----------------------------

_VOCAB_ITEMS_EN: list[dict[str, str]] = [
    {
        "word": "bank", "sentence": "We sat by the bank of the river to watch the sunset.",
        "correct": "the land alongside a river", "misconception": "a place that keeps and lends money",
        "distractor_a": "to turn an airplane sharply", "distractor_b": "a row of switches on a machine",
    },
    {
        "word": "bat", "sentence": "A bat flew out of the cave at dusk.",
        "correct": "a flying nocturnal mammal", "misconception": "a wooden club used in baseball",
        "distractor_a": "to blink rapidly", "distractor_b": "a type of hat",
    },
    {
        "word": "spring", "sentence": "The hikers filled their bottles from a spring in the forest.",
        "correct": "a natural source of water flowing from the ground", "misconception": "the season after winter",
        "distractor_a": "a coiled piece of metal", "distractor_b": "to jump suddenly",
    },
    {
        "word": "trunk", "sentence": "The elephant used its trunk to grab the fruit.",
        "correct": "an elephant's long nose", "misconception": "the storage area of a car",
        "distractor_a": "the main stem of a tree", "distractor_b": "a large suitcase",
    },
]

_VOCAB_ITEMS_VI: list[dict[str, str]] = [
    {
        "word": "đồng", "sentence": "Cánh đồng lúa chín vàng rực dưới nắng.",
        "correct": "khoảng đất rộng để trồng trọt", "misconception": "đơn vị tiền tệ",
        "distractor_a": "kim loại màu đỏ (đồng thau)", "distractor_b": "cùng nhau, giống nhau",
    },
    {
        "word": "đá", "sentence": "Anh ấy đá quả bóng vào lưới.",
        "correct": "dùng chân hất mạnh vào vật gì", "misconception": "chất rắn cứng như đá núi",
        "distractor_a": "chất lỏng đông cứng do lạnh", "distractor_b": "một loại đồ uống có đá lạnh",
    },
    {
        "word": "chín", "sentence": "Quả xoài đã chín vàng, rất ngọt.",
        "correct": "quả đã đến độ ăn được, không còn xanh", "misconception": "con số 9",
        "distractor_a": "được nấu kỹ (cơm chín)", "distractor_b": "thành thạo, giỏi giang",
    },
    {
        "word": "để", "sentence": "Mẹ để chiếc cặp lên bàn trước khi đi làm.",
        "correct": "đặt một vật xuống một chỗ", "misconception": "nhằm mục đích, với mục tiêu",
        "distractor_a": "cho phép, không ngăn cản", "distractor_b": "còn lại, còn dư",
    },
]


def _grade35_question(rng: random.Random, index: int, target_language: str) -> FixedAnswerQuestion:
    resolved = _resolve_target_language(target_language)
    items = _VOCAB_ITEMS_VI if resolved == "vi" else _VOCAB_ITEMS_EN
    item = items[index % len(items)]
    word, sentence = item["word"], item["sentence"]
    correct, misconception, distractor_a, distractor_b = (
        item["correct"], item["misconception"], item["distractor_a"], item["distractor_b"],
    )
    if resolved == "vi":
        prompt_en = f'In the sentence "{sentence}", what does "{word}" mean here?'
        prompt_vi = f'Trong câu "{sentence}", từ "{word}" ở đây có nghĩa là gì?'
        explain_en = f'Context ("{sentence}") points to "{correct}", not the more familiar meaning "{misconception}".'
        explain_vi = f'Ngữ cảnh ("{sentence}") cho thấy nghĩa đúng là "{correct}", không phải nghĩa quen thuộc hơn "{misconception}".'
    else:
        prompt_en = f'In the sentence "{sentence}", what does "{word}" mean here?'
        prompt_vi = f'Trong câu tiếng Anh "{sentence}", từ "{word}" ở đây nghĩa là gì?'
        explain_en = f'Context ("{sentence}") points to "{correct}", not the more familiar meaning "{misconception}".'
        explain_vi = f'Ngữ cảnh ("{sentence}") cho thấy nghĩa đúng là "{correct}", không phải nghĩa quen thuộc hơn "{misconception}".'
    return build_fixed_answer_question(
        id_prefix="language_literacy", index=index, grade_band=GradeBand.GRADES_3_5,
        standard_code=_STANDARD_CODE_BY_BAND[GradeBand.GRADES_3_5],
        misconception_id=_MISCONCEPTION_ID_BY_BAND[GradeBand.GRADES_3_5][resolved],
        prompt_en=prompt_en, prompt_vi=prompt_vi,
        correct_en=correct, correct_vi=correct,
        misconception_en=misconception, misconception_vi=misconception,
        distractor_a_en=distractor_a, distractor_a_vi=distractor_a,
        distractor_b_en=distractor_b, distractor_b_vi=distractor_b,
        explain_en=explain_en, explain_vi=explain_vi,
    )


# -- Grades 6-8: grammar (EN subject-verb agreement / VI classifiers) -------

_GRAMMAR_ITEMS_EN: list[dict[str, str]] = [
    {
        "sentence": "Neither the players nor the coach ___ ready.",
        "correct": "is", "misconception": "are", "distractor_a": "was", "distractor_b": "were",
    },
    {
        "sentence": "Either the teacher or the students ___ responsible for the trip.",
        "correct": "are", "misconception": "is", "distractor_a": "was", "distractor_b": "am",
    },
    {
        "sentence": "Neither the dogs nor the cat ___ hungry.",
        "correct": "is", "misconception": "are", "distractor_a": "were", "distractor_b": "am",
    },
]

_GRAMMAR_ITEMS_VI: list[dict[str, str]] = [
    {
        "sentence": "Tôi mua một ___ sách mới.",
        "correct": "quyển", "misconception": "con", "distractor_a": "cái", "distractor_b": "chiếc",
    },
    {
        "sentence": "Anh ấy có hai ___ chó rất đáng yêu.",
        "correct": "con", "misconception": "cái", "distractor_a": "chiếc", "distractor_b": "quyển",
    },
    {
        "sentence": "Cô ấy mặc một ___ áo dài màu đỏ.",
        "correct": "chiếc", "misconception": "con", "distractor_a": "cái", "distractor_b": "quyển",
    },
]


def _grade68_question(rng: random.Random, index: int, target_language: str) -> FixedAnswerQuestion:
    resolved = _resolve_target_language(target_language)
    items = _GRAMMAR_ITEMS_VI if resolved == "vi" else _GRAMMAR_ITEMS_EN
    item = items[index % len(items)]
    sentence = item["sentence"]
    correct, misconception, distractor_a, distractor_b = (
        item["correct"], item["misconception"], item["distractor_a"], item["distractor_b"],
    )
    if resolved == "vi":
        prompt_en = f'Fill in the blank with the correct classifier (loại từ): "{sentence}"'
        prompt_vi = f'Điền loại từ đúng vào chỗ trống: "{sentence}"'
        explain_en = f'"{correct}" is the classifier that matches this noun\'s category; "{misconception}" over-applies the animal classifier as a default.'
        explain_vi = f'"{correct}" là loại từ phù hợp với danh từ này; "{misconception}" là lạm dụng loại từ chỉ động vật làm mặc định.'
    else:
        prompt_en = f'Fill in the blank with the correct verb form: "{sentence}"'
        prompt_vi = f'Điền dạng động từ đúng vào chỗ trống trong câu tiếng Anh: "{sentence}"'
        explain_en = f'"{correct}" agrees with the subject nearest the verb; "{misconception}" wrongly agrees with the first-listed subject instead.'
        explain_vi = f'"{correct}" hòa hợp với chủ ngữ gần động từ nhất; "{misconception}" hòa hợp sai với chủ ngữ được liệt kê đầu tiên.'
    return build_fixed_answer_question(
        id_prefix="language_literacy", index=index, grade_band=GradeBand.GRADES_6_8,
        standard_code=_STANDARD_CODE_BY_BAND[GradeBand.GRADES_6_8],
        misconception_id=_MISCONCEPTION_ID_BY_BAND[GradeBand.GRADES_6_8][resolved],
        prompt_en=prompt_en, prompt_vi=prompt_vi,
        correct_en=correct, correct_vi=correct,
        misconception_en=misconception, misconception_vi=misconception,
        distractor_a_en=distractor_a, distractor_a_vi=distractor_a,
        distractor_b_en=distractor_b, distractor_b_vi=distractor_b,
        explain_en=explain_en, explain_vi=explain_vi,
    )


# -- Grades 9-12: reading comprehension (main idea synthesis) ---------------

_READING_ITEMS_EN: list[dict[str, str]] = [
    {
        "passage": (
            "Rising sea levels threaten coastal cities worldwide. Engineers are building sea walls, "
            "elevating buildings, and restoring wetlands to slow the damage. Still, many experts warn "
            "that adaptation alone will not be enough without cutting emissions."
        ),
        "correct": "Coastal cities are adapting to rising seas, but experts say emission cuts are also needed.",
        "misconception": "Rising sea levels threaten coastal cities worldwide.",
        "distractor_a": "Engineers only build sea walls to stop flooding.",
        "distractor_b": "Wetlands restoration has replaced all other flood defenses.",
    },
    {
        "passage": (
            "Social media use among teenagers has risen sharply over the past decade. Some studies link "
            "heavy use to anxiety and poor sleep, while others find no clear effect once other factors are "
            "controlled for. Researchers agree that more long-term study is needed before drawing firm "
            "conclusions."
        ),
        "correct": "The link between teen social media use and mental health is still unsettled and needs more research.",
        "misconception": "Social media use among teenagers has risen sharply over the past decade.",
        "distractor_a": "Studies prove social media causes anxiety in all teenagers.",
        "distractor_b": "Researchers have concluded social media has no effect on teens.",
    },
]

_READING_ITEMS_VI: list[dict[str, str]] = [
    {
        "passage": (
            "Rừng ngập mặn ven biển đang bị thu hẹp do nuôi trồng thủy sản. Diện tích rừng giảm khiến bờ "
            "biển dễ bị xói lở hơn khi có bão. Nhiều địa phương đã bắt đầu trồng lại rừng để bảo vệ bờ biển."
        ),
        "correct": "Rừng ngập mặn bị thu hẹp làm bờ biển dễ xói lở, nên nhiều nơi đang trồng lại rừng để bảo vệ bờ biển.",
        "misconception": "Rừng ngập mặn ven biển đang bị thu hẹp do nuôi trồng thủy sản.",
        "distractor_a": "Toàn bộ rừng ngập mặn ven biển đã biến mất.",
        "distractor_b": "Nuôi trồng thủy sản đã bị cấm hoàn toàn ở vùng ven biển.",
    },
    {
        "passage": (
            "Học sinh ngày càng dành nhiều thời gian cho mạng xã hội. Một số nghiên cứu cho thấy điều này "
            "liên quan đến lo âu và mất ngủ, nhưng số khác lại không tìm thấy ảnh hưởng rõ ràng. Các nhà "
            "nghiên cứu cho rằng cần thêm thời gian để có kết luận chắc chắn."
        ),
        "correct": "Mối liên hệ giữa việc dùng mạng xã hội và sức khỏe tâm lý của học sinh vẫn chưa rõ ràng, cần nghiên cứu thêm.",
        "misconception": "Học sinh ngày càng dành nhiều thời gian cho mạng xã hội.",
        "distractor_a": "Mạng xã hội chắc chắn gây lo âu cho mọi học sinh.",
        "distractor_b": "Các nhà nghiên cứu đã kết luận mạng xã hội không ảnh hưởng gì.",
    },
]


def _grade912_question(rng: random.Random, index: int, target_language: str) -> FixedAnswerQuestion:
    resolved = _resolve_target_language(target_language)
    items = _READING_ITEMS_VI if resolved == "vi" else _READING_ITEMS_EN
    item = items[index % len(items)]
    passage = item["passage"]
    correct, misconception, distractor_a, distractor_b = (
        item["correct"], item["misconception"], item["distractor_a"], item["distractor_b"],
    )
    if resolved == "vi":
        prompt_en = f'What is the main idea (luận điểm chính) of this passage? "{passage}"'
        prompt_vi = f'Luận điểm chính của đoạn văn sau là gì? "{passage}"'
    else:
        prompt_en = f'What is the main idea of this passage? "{passage}"'
        prompt_vi = f'Ý chính của đoạn văn tiếng Anh sau là gì? "{passage}"'
    explain_en = f'The passage synthesizes to "{correct}"; its literal first sentence, "{misconception}", is only a starting detail, not the full central claim.'
    explain_vi = f'Đoạn văn tổng hợp thành ý "{correct}"; câu đầu tiên, "{misconception}", chỉ là một chi tiết mở đầu, chưa phải luận điểm đầy đủ.'
    return build_fixed_answer_question(
        id_prefix="language_literacy", index=index, grade_band=GradeBand.GRADES_9_12,
        standard_code=_STANDARD_CODE_BY_BAND[GradeBand.GRADES_9_12],
        misconception_id=_MISCONCEPTION_ID_BY_BAND[GradeBand.GRADES_9_12][resolved],
        prompt_en=prompt_en, prompt_vi=prompt_vi,
        correct_en=correct, correct_vi=correct,
        misconception_en=misconception, misconception_vi=misconception,
        distractor_a_en=distractor_a, distractor_a_vi=distractor_a,
        distractor_b_en=distractor_b, distractor_b_vi=distractor_b,
        explain_en=explain_en, explain_vi=explain_vi,
    )


_GENERATORS: dict[GradeBand, Callable[[random.Random, int, str], FixedAnswerQuestion]] = {
    GradeBand.K_2: _k2_question,
    GradeBand.GRADES_3_5: _grade35_question,
    GradeBand.GRADES_6_8: _grade68_question,
    GradeBand.GRADES_9_12: _grade912_question,
}


def build_language_literacy_questions(
    grade_band: GradeBand, *, count: int = 4, seed: int = 0, target_language: str = "en",
) -> list[FixedAnswerQuestion]:
    """Deterministic given the same `seed` + `target_language` -- same
    inputs always produce the same problem set (mirrors #447/#448's
    deterministic-and-traceable requirement)."""
    rng = random.Random(seed)
    generator = _GENERATORS[grade_band]
    return [generator(rng, index, target_language) for index in range(count)]
