import { describe, expect, it } from "vitest";
import { renderArtifact } from "../src/renderer.js";

describe("template-library — quiz page", () => {
  it("renders question prompt", async () => {
    const html = await renderArtifact("quiz", {
      title: "Test Quiz",
      subject: "English",
      gradeLevel: "Grade 8",
      questions: [{
        id: "q1",
        prompt: "What is the capital of France?",
        options: [{ label: "A", text: "London" }, { label: "B", text: "Paris" }],
        answer: "B",
      }],
    });
    expect(html).toContain("What is the capital of France?");
    expect(html).toContain("London");
    expect(html).toContain("Paris");
  });

  it("renders question options as radio inputs", async () => {
    const html = await renderArtifact("quiz", {
      title: "Quiz",
      subject: "Science",
      gradeLevel: "Grade 5",
      questions: [{
        id: "q1",
        prompt: "2 + 2 = ?",
        options: [{ label: "A", text: "3" }, { label: "B", text: "4" }],
        answer: "B",
      }],
    });
    expect(html).toContain('type="radio"');
    expect(html).toContain('role="radiogroup"');
  });

  it("has no external URLs", async () => {
    const html = await renderArtifact("quiz", {
      title: "Quiz",
      subject: "Math",
      gradeLevel: "Grade 6",
      questions: [],
    });
    expect(html).not.toMatch(/https?:\/\//);
  });
});

describe("template-library — lesson page", () => {
  it("renders learning objectives", async () => {
    const html = await renderArtifact("lesson", {
      title: "Lesson",
      subject: "Math",
      gradeLevel: "Grade 5",
      objectives: ["Understand fractions", "Apply fractions"],
      sections: [],
    });
    expect(html).toContain("Understand fractions");
    expect(html).toContain("Apply fractions");
  });

  it("renders section content", async () => {
    const html = await renderArtifact("lesson", {
      title: "Lesson",
      subject: "Math",
      gradeLevel: "Grade 5",
      objectives: [],
      sections: [{ heading: "Introduction", body: "Welcome to math." }],
    });
    expect(html).toContain("Introduction");
    expect(html).toContain("Welcome to math.");
  });

  it("renders vocabulary section", async () => {
    const html = await renderArtifact("lesson", {
      title: "Lesson",
      subject: "English",
      gradeLevel: "Grade 7",
      objectives: [],
      sections: [],
      vocabulary: [{ term: "photosynthesis", definition: "Process by which plants make food" }],
    });
    expect(html).toContain("photosynthesis");
    expect(html).toContain("Process by which plants make food");
  });
});

describe("template-library — answer_key page", () => {
  it("shows all answers (no hide/reveal toggle)", async () => {
    const html = await renderArtifact("answer_key", {
      title: "Answer Key",
      sections: [{
        id: "s1",
        title: "Toán học",
        group: "a",
        components: [{
          type: "question_card",
          id: "ak1",
          text: "5 + 3 = ?",
          options: { A: "7", B: "8" },
          answer: "B",
          explain: "5 + 3 equals 8",
        }],
      }],
    });
    expect(html).toContain("5 + 3 = ?");
    expect(html).toContain("5 + 3 equals 8");
    expect(html).toContain("option correct");
  });

  it("renders answer key eyebrow and title", async () => {
    const html = await renderArtifact("answer_key", {
      title: "Answer Key",
      sections: [],
    });
    expect(html).toContain("Đáp án chi tiết");
    expect(html).toContain("Answer Key");
  });
});

describe("template-library — flashcard_deck page", () => {
  it("renders card fronts and backs", async () => {
    const html = await renderArtifact("flashcard_deck", {
      title: "Vocab Flashcards",
      subject: "English",
      gradeLevel: "Grade 6",
      cards: [{ id: "c1", front: "apple", back: "quả táo" }],
    });
    expect(html).toContain("apple");
    expect(html).toContain("quả táo");
  });

  it("includes navigation buttons", async () => {
    const html = await renderArtifact("flashcard_deck", {
      title: "Flashcards",
      subject: "English",
      gradeLevel: "Grade 6",
      cards: [
        { id: "c1", front: "cat", back: "mèo" },
        { id: "c2", front: "dog", back: "chó" },
      ],
    });
    expect(html).toContain("btn-prev");
    expect(html).toContain("btn-next");
  });
});

describe("template-library — exit_ticket page", () => {
  it("limits to 3 questions", async () => {
    const html = await renderArtifact("exit_ticket", {
      title: "Exit Ticket",
      subject: "Math",
      gradeLevel: "Grade 5",
      questions: [
        { id: "et1", prompt: "Q1?", type: "short_answer" },
        { id: "et2", prompt: "Q2?", type: "short_answer" },
        { id: "et3", prompt: "Q3?", type: "short_answer" },
        { id: "et4", prompt: "Q4 — should not appear", type: "short_answer" },
      ],
    });
    expect(html).toContain("Q1?");
    expect(html).toContain("Q3?");
    expect(html).not.toContain("Q4");
  });
});

describe("template-library — reading_passage page", () => {
  it("renders the passage text", async () => {
    const html = await renderArtifact("reading_passage", {
      title: "The Fox",
      subject: "English",
      gradeLevel: "Grade 7",
      passage: "The quick brown fox jumps over the lazy dog.",
      questions: [],
    });
    expect(html).toContain("The quick brown fox");
  });

  it("renders comprehension questions", async () => {
    const html = await renderArtifact("reading_passage", {
      title: "Reading",
      subject: "English",
      gradeLevel: "Grade 7",
      passage: "Some text here.",
      questions: [{
        id: "rq1",
        prompt: "What is the main idea?",
        answer: "test",
        type: "short_answer",
      }],
    });
    expect(html).toContain("What is the main idea?");
  });
});

describe("template-library — vocab lesson page (Report 09)", () => {
  it("renders sidebar title and nav links when sidebar is provided", async () => {
    const html = await renderArtifact("lesson", {
      title: "Unit 2: Travel and Transport",
      subject: "English",
      gradeLevel: "Grade 10",
      sidebar: {
        title: "Unit 2 — Travel and Transport",
        subtitle: "Destination B2 · Vocab lesson",
        stats: [{ key: "Thời lượng", value: "~100 phút" }],
        nav: [
          { href: "#warmup", num: "1", label: "Khởi động — phim" },
          { href: "#concept", num: "2", label: "Bản đồ đối chiếu" },
        ],
        linkback: "Buổi học này áp dụng phương pháp đối chiếu.",
      },
      sections: [],
    });
    expect(html).toContain("Unit 2 — Travel and Transport");
    expect(html).toContain("Khởi động — phim");
    expect(html).toContain("#warmup");
    expect(html).toContain("~100 phút");
  });

  it("renders hero with eyebrow, lede, note-box, stat-cards, and objectives", async () => {
    const html = await renderArtifact("lesson", {
      title: "Unit 2: Travel",
      hero: {
        eyebrow: "Buổi học mẫu #1",
        lede: "Giáo án thiết kế theo phương pháp đối chiếu.",
        noteBox: "<b>Điểm đặc biệt:</b> arrive / reach / enter.",
        statCards: [
          { label: "Trọng tâm từ vựng", value: "6 cặp", unit: "đối chiếu" },
          { label: "Phrasal verbs", value: "15", unit: "theo 5 cụm" },
        ],
        objectives: [
          "Phân biệt <b>arrive / reach / enter</b>",
          "Dùng 15 phrasal verbs theo 5 cụm nghĩa",
        ],
      },
      sections: [],
    });
    expect(html).toContain("Buổi học mẫu #1");
    expect(html).toContain("phương pháp đối chiếu");
    expect(html).toContain("Điểm đặc biệt");
    expect(html).toContain("6 cặp");
    expect(html).toContain("Phrasal verbs");
    expect(html).toContain("arrive / reach / enter");
  });

  it("renders section with time badge", async () => {
    const html = await renderArtifact("lesson", {
      title: "Lesson",
      sections: [
        { id: "warmup", heading: "1. Khởi động bằng phim", time: "10–12 phút", body: "Watch and spot vocabulary." },
      ],
    });
    expect(html).toContain("Khởi động bằng phim");
    expect(html).toContain("10–12 phút");
    expect(html).toContain("Watch and spot vocabulary");
    expect(html).toContain('id="warmup"');
  });

  it("renders film_clip_activity component via dispatcher", async () => {
    const html = await renderArtifact("lesson", {
      title: "Film Lesson",
      sections: [{
        heading: "Warm-up",
        components: [{
          type: "film_clip_activity",
          clips: [
            { title: "Up in the Air (2009)", description: "Airport scenes with travel vocabulary." },
          ],
          hunt_chips: ["check in", "set off", "arrive"],
          post_viewing_note: "Ask: which word did you spot first?",
        }],
      }],
    });
    expect(html).toContain("Up in the Air");
    expect(html).toContain("Airport scenes");
    expect(html).toContain("check in");
    expect(html).toContain("set off");
    expect(html).toContain("spot first");
  });

  it("renders vocab_cluster component via dispatcher", async () => {
    const html = await renderArtifact("lesson", {
      title: "Vocab Lesson",
      sections: [{
        heading: "Concepts",
        components: [{
          type: "vocab_cluster",
          title: "arrive / reach / enter",
          description: "Three verbs of arrival — each with a distinct semantic niche.",
          items: [
            { word: "ENTER", definition: "Go INTO a bounded space — no preposition.", example: "He entered the room." },
            { word: "ARRIVE (at/in)", definition: "Reach a point — preposition required.", example: "We arrived at the station." },
            { word: "REACH", definition: "Get somewhere after effort — no preposition.", example: "We reached the summit." },
          ],
          discrimination_prompt: "Which verb for entering a specific room?",
        }],
      }],
    });
    expect(html).toContain("arrive / reach / enter");
    expect(html).toContain("ENTER");
    expect(html).toContain("ARRIVE");
    expect(html).toContain("REACH");
    expect(html).toContain("entered the room");
    expect(html).toContain("Which verb for entering");
  });

  it("renders phrasal_verb_cluster component via dispatcher", async () => {
    const html = await renderArtifact("lesson", {
      title: "Phrasal Verbs",
      sections: [{
        heading: "Clusters",
        components: [{
          type: "phrasal_verb_cluster",
          groups: [
            { label: "Rời đi", color: "a", items: [
              { verb: "set off", meaning: "bắt đầu hành trình", example: "We set off at dawn." },
              { verb: "go away", meaning: "đi nghỉ" },
            ]},
            { label: "Đến nơi", color: "b", items: [
              { verb: "get back", meaning: "trở về" },
            ]},
          ],
        }],
      }],
    });
    expect(html).toContain("Rời đi");
    expect(html).toContain("set off");
    expect(html).toContain("bắt đầu hành trình");
    expect(html).toContain("Đến nơi");
    expect(html).toContain("get back");
  });

  it("renders roleplay_script component via dispatcher with blanks (answer key hidden in student lesson)", async () => {
    const html = await renderArtifact("lesson", {
      title: "Roleplay",
      sections: [{
        heading: "Roleplay",
        components: [{
          type: "roleplay_script",
          instruction: "Read along — do not improvise.",
          lines: [
            { speaker: "Người tiễn (A)", speaker_class: "A", text: "We should [blank_1] soon." },
            { speaker: "Người đi (B)", speaker_class: "B", text: "I don't want to [blank_2] the flight." },
          ],
          answer_key: ["set off", "miss"],
        }],
      }],
    });
    expect(html).toContain("Read along");
    expect(html).toContain("Người tiễn (A)");
    expect(html).toContain("(1)");
    expect(html).toContain("(2)");
    expect(html).not.toContain("set off");
    expect(html).not.toContain("miss");
  });

  it("renders contrastive_pairs component via dispatcher", async () => {
    const html = await renderArtifact("lesson", {
      title: "Quick Pairs",
      sections: [{
        heading: "Contrast",
        components: [{
          type: "contrastive_pairs",
          title: "Rapid-fire contrast",
          rows: [
            { terms: "fare / ticket / fee", distinction: "fare=price on transport, ticket=physical card, fee=service charge" },
            { terms: "miss / lose", distinction: "miss=fail to catch vehicle, lose=misplace an object" },
          ],
        }],
      }],
    });
    expect(html).toContain("fare / ticket / fee");
    expect(html).toContain("price on transport");
    expect(html).toContain("miss / lose");
  });

  it("renders hw_list component via dispatcher", async () => {
    const html = await renderArtifact("lesson", {
      title: "HW",
      sections: [{
        heading: "Homework",
        components: [{
          type: "hw_list",
          items: [
            { tag: "[a]", text: "Exercise B, D, E in textbook pages 13–15." },
            { tag: "[a]", text: "Write 5 sentences using phrasal verbs." },
          ],
          callout: "Tag all homework in Classroom as <b>[a] Travel vocab</b>.",
        }],
      }],
    });
    expect(html).toContain("[a]");
    expect(html).toContain("Exercise B, D, E");
    expect(html).toContain("Write 5 sentences");
    expect(html).toContain("Travel vocab");
  });

  it("renders question_mc with wrong_reasons and essence when showAnswer is set", async () => {
    // question_mc.html with showAnswer=true shows wrong reasons
    const { eta } = await import("../src/eta-engine.js");
    const html = await eta.renderAsync("components/question_mc", {
      id: "q1",
      index: 1,
      prompt: "By the time we ________ the summit, the sun had set.",
      options: [
        { label: "A", text: "arrived" },
        { label: "B", text: "reached" },
        { label: "C", text: "entered" },
      ],
      answer: "B",
      explain: "Reach + noun (no preposition) for effort-journey.",
      showAnswer: true,
      wrong_reasons: {
        A: "arrive requires a preposition (at/in)",
        C: "enter is for bounded spaces like rooms",
      },
      essence: "REACH = effort-journey without preposition",
      tip: "No preposition after reach → journey sense",
    });
    expect(html).toContain("arrive requires a preposition");
    expect(html).toContain("enter is for bounded spaces");
    expect(html).toContain("REACH = effort-journey");
    expect(html).toContain("No preposition after reach");
  });

  it("has no external URLs in full vocab lesson output", async () => {
    const html = await renderArtifact("lesson", {
      title: "Unit 2",
      sidebar: { title: "Unit 2", nav: [{ href: "#s1", label: "Section 1" }] },
      hero: { eyebrow: "Test", lede: "Introduction" },
      sections: [
        { id: "s1", heading: "Film", time: "10 min", components: [
          { type: "film_clip_activity", clips: [{ title: "Movie", description: "desc" }], hunt_chips: ["arrive"] }
        ]},
      ],
    });
    expect(html).not.toMatch(/https?:\/\//);
  });
});
