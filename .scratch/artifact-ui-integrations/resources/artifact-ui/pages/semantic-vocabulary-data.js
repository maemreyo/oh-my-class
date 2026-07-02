// Realistic SemanticAnchorCluster-shaped content (ADR-022 §1) used to
// render the semantic-vocabulary showcase. Field names mirror the ADR's
// proposed contract so this can be swapped for real pipeline output
// later without changing the render functions.

const clusters = [
  {
    id: "cluster-01-travel",
    status: "passed",
    groupLabel: "Nhóm 01",
    title: 'Các thể loại "chuyến đi"',
    subtitle: "5 từ tưởng như đồng nghĩa — nhưng mang 5 bối cảnh hoàn toàn khác nhau.",
    accentCat: "cat1",
    terms: [
      {
        word: "Voyage",
        impression: "Hoành tráng",
        coreTrigger: "Explore",
        visualCue: "Tàu thủy lớn / phi thuyền",
        studentExplanation:
          "Chuyến đi mang tính lịch sử — vượt đại dương hoặc lao vào vũ trụ. Không dành cho một buổi dạo chơi ngắm cảnh thông thường.",
        example: "Darwin's five-year voyage on HMS Beagle reshaped modern biology.",
        contrastNote: "Khác Journey ở quy mô: Voyage luôn gắn với phương tiện lớn (tàu/phi thuyền), không đi bộ hay lái xe.",
        teacherScript:
          '"Nói đến Voyage là nói đến Columbus khám phá châu Mỹ, hay tàu Apollo bay vào vũ trụ. Nó phải có mùi vị của sự hoành tráng và thám hiểm."',
        sourceNotes: "Cambridge Dictionary; Oxford Collocations Dictionary — collocates chủ yếu với sea/space.",
        edgeCases: "Học sinh dễ dùng \"voyage\" cho công tác ngắn ngày — cần nhấn mạnh yếu tố \"lịch sử, quy mô lớn\".",
      },
      {
        word: "Journey",
        impression: "Gian khổ",
        coreTrigger: "Path",
        visualCue: "Nhiều stop points",
        studentExplanation:
          "Ăn nhau ở quá trình đi — đường dài, mệt mỏi, từ điểm A đến điểm B qua nhiều chặng. Đích đến đôi khi không quan trọng bằng trải nghiệm trên đường.",
        example: "Her four-year journey through university taught her more than any single lecture.",
        contrastNote: "Khác Trip ở trọng tâm: Journey nhấn vào quá trình di chuyển, Trip nhấn vào mục đích và điểm đến.",
        teacherScript:
          '"Journey không phải là đi chơi. Đó là hành trình đi bộ xuyên Việt, hay 4 năm xa nhà đi học đầy gian nan. Nghĩ đến Journey là nghĩ đến đôi chân mỏi và những trạm dừng."',
        sourceNotes: "Merriam-Webster; Longman Collocations — thường dùng ẩn dụ (life journey, learning journey).",
        edgeCases: "Có thể dùng phi vật lý (a journey of self-discovery) — nên giới thiệu nghĩa ẩn dụ ở buổi sau.",
      },
      {
        word: "Trip",
        impression: "Nhanh gọn",
        coreTrigger: "Purpose",
        visualCue: "Return chắc chắn",
        studentExplanation:
          "Thực dụng nhất trong nhóm: đi có việc → đến nơi làm việc đó → quay về đúng chỗ cũ. Ngắn ngày, nhấn mạnh vào đích đến và mục đích.",
        example: "He took a two-day business trip to Da Nang and flew back on Friday.",
        contrastNote: "Khác Excursion ở mục đích: Trip có thể vì công việc, Excursion luôn để giải trí/thư giãn.",
        teacherScript:
          '"Trip giống một chiếc lò xo bật đi rồi bật lại. Business trip, school trip — vài ngày rồi về nhà ngủ. Đích đến và mục đích là tối thượng."',
        sourceNotes: "Cambridge Dictionary — countable noun, luôn đi kèm mục đích cụ thể (business/school/field trip).",
        edgeCases: "Đây là từ trung tính nhất — học sinh có xu hướng dùng Trip cho mọi loại chuyến đi, cần phân biệt rõ với 4 từ còn lại.",
      },
      {
        word: "Travel",
        impression: "Trừu tượng",
        coreTrigger: "Concept",
        visualCue: "Industry / khái niệm vĩ mô",
        studentExplanation:
          "Không phải một chuyến đi cụ thể. Là khái niệm vĩ mô chỉ hành động dịch chuyển, hoặc cả ngành công nghiệp du lịch — nên không đếm được.",
        example: "Air travel became significantly cheaper after low-cost carriers entered the market.",
        contrastNote: "Khác 4 từ còn lại: Travel là danh từ không đếm được (uncountable) — không có \"a travel\" hay \"two travels\".",
        teacherScript:
          '"Travel to lớn, chung chung — như \'air travel\' hay \'I love travel\'. Đừng bao giờ đếm 1 travel, 2 travel."',
        sourceNotes: "Oxford Learner's Dictionary — lưu ý rõ (uncountable) trong mục từ.",
        edgeCases: "Lỗi phổ biến nhất trong nhóm: học sinh viết \"a travel to Japan\" — cần chữa ngay khi gặp.",
      },
      {
        word: "Excursion",
        impression: "Vui vẻ",
        coreTrigger: "Group",
        visualCue: "Picnic / dã ngoại",
        studentExplanation:
          "Chuyến \"đổi gió\" ngắn ngày. Mấu chốt là vui vẻ, thư giãn, thường đi theo một tập thể theo lịch trình đã lên sẵn.",
        example: "The class went on a weekend excursion to the botanical garden.",
        contrastNote: "Khác Trip ở cảm xúc: Excursion luôn vui vẻ/giải trí, không bao giờ mang tính công việc.",
        teacherScript:
          '"Excursion là khi cả lớp rủ nhau đi picnic cuối tuần ở ngoại ô. Không khí hội hè, vui tươi, ngắn ngủi."',
        sourceNotes: "Longman Dictionary — thường đi cùng \"organised/group\".",
        edgeCases: "Ít gặp trong văn nói hàng ngày hơn 4 từ còn lại — nhấn học sinh dùng đúng ngữ cảnh trang trọng/lịch trình có tổ chức.",
      },
    ],
  },
  {
    id: "cluster-02-fare",
    status: "passed",
    groupLabel: "Nhóm 02",
    title: 'Các thể loại "tiền vé"',
    subtitle: "3 từ đều chỉ tiền — nhưng bạn trả cho ba thứ hoàn toàn khác nhau.",
    accentCat: "cat2",
    terms: [
      {
        word: "Fare",
        impression: "Di chuyển",
        coreTrigger: "Vehicle",
        visualCue: "Engine / bánh xe lăn",
        studentExplanation:
          "Số tiền trả cho bánh xe lăn. Bất kỳ phương tiện nào có động cơ chở bạn từ chỗ này sang chỗ khác, tiền đó là Fare.",
        example: "The bus fare went up by two thousand dong this month.",
        contrastNote: "Khác Ticket ở bản chất: Fare là số tiền (trừu tượng), Ticket là vật bạn cầm sau khi trả Fare.",
        teacherScript: '"Nghĩ đến Fare là nghĩ đến tiếng còi xe, tiếng động cơ tàu hỏa. Bạn trả tiền để người ta chở bạn đi."',
        sourceNotes: "Cambridge Dictionary — collocates: bus/taxi/train fare.",
        edgeCases: "Học sinh hay nhầm Fare với Fee khi nói vé máy bay — nhấn mạnh Fare luôn gắn với phương tiện có động cơ.",
      },
      {
        word: "Ticket",
        impression: "Vật lý",
        coreTrigger: "Paper / QR code",
        visualCue: "Gate pass",
        studentExplanation:
          "Một vật thể cứng — mảnh giấy, thẻ từ, hay mã QR bạn chìa ra cho người ta soát. Tấm thông hành để được lên xe hoặc vào cửa.",
        example: "Don't lose your ticket — you'll need to show it at the gate.",
        contrastNote: "Fare là tiền trừu tượng, còn Ticket là cái vé giấy bạn cầm trên tay. Bạn dùng Fare để mua Ticket.",
        teacherScript: '"Fare là tiền trừu tượng, còn Ticket là cái vé giấy bạn cầm trên tay. Bạn dùng Fare để mua Ticket."',
        sourceNotes: "Cambridge Dictionary — countable noun, vật thể cụ thể.",
        edgeCases: "Không nhầm với Fee dù cả hai đều liên quan \"vào cửa\" — Ticket luôn là vật thể, Fee luôn là khoản phí trừu tượng.",
      },
      {
        word: "Fee",
        impression: "Quy định",
        coreTrigger: "Service",
        visualCue: "Institution",
        studentExplanation:
          "Tiền trả cho dịch vụ, luật lệ hoặc tổ chức. Không trả cho bánh xe lăn, mà cho chất xám, quyền truy cập, hay phí thủ tục.",
        example: "The museum charges an admission fee of fifty thousand dong for adults.",
        contrastNote: "Khác Fare hoàn toàn: Fee không có phương tiện di chuyển liên quan — luôn là tổ chức/dịch vụ.",
        teacherScript: '"Vào bảo tàng, vào trường thì trả Fee (admission fee, tuition fee). Không có xe cộ nào chở bạn ở đây cả."',
        sourceNotes: "Oxford Collocations Dictionary — collocates: admission/tuition/service fee.",
        edgeCases: "Late fee, service fee cũng thuộc nhóm này — mở rộng cho học sinh khá khi ôn tập.",
      },
    ],
  },
  {
    id: "cluster-03-compensate",
    status: "needs_review",
    groupLabel: "Nhóm 03",
    title: 'Các thể loại "đền bù"',
    subtitle: "3 từ cùng nói về việc bù đắp thiệt hại — ranh giới ngữ nghĩa mỏng, cần giáo viên xác nhận trước khi phát cho học sinh.",
    accentCat: "cat3",
    reviewReason:
      "Chỉ tìm được 1 nguồn đáng tin cậy phân biệt rõ sắc thái \"refund\" so với \"reimburse\" trong ngữ cảnh phi tài chính — dưới ngưỡng tối thiểu 2 nguồn độc lập của chính sách standard (ADR-021 §5).",
    reviewSuggestion:
      "Giáo viên xác nhận ví dụ \"refund\" trong ngữ cảnh phi mua-bán (vd. refund of trust) trước khi duyệt xuất bản cho học sinh.",
    parseConfidence: "0.61 — dưới ngưỡng tự động duyệt (0.75)",
    terms: [
      {
        word: "Compensate",
        impression: "Chủ động",
        coreTrigger: "Equivalent value",
        visualCue: "Trao lại giá trị tương đương",
        studentExplanation:
          "Chủ động trao lại một giá trị/vật thay thế tương đương cho thiệt hại đã gây ra — không chỉ xin lỗi hay sửa chữa đơn thuần.",
        example: "The airline compensated passengers with a full refund and a travel voucher.",
        contrastNote: "Khác Reimburse: Compensate có thể là bất kỳ hình thức đền bù nào (tiền, vật, dịch vụ), không chỉ tiền mặt.",
        teacherScript:
          '"Compensation là khi bạn làm hỏng sách của bạn và đền một cuốn mới kèm một cử chỉ thiện chí — chủ động bù đắp giá trị tương đương."',
        sourceNotes: "Cambridge Dictionary. [CẦN THÊM 1 NGUỒN — xem review reason]",
        edgeCases: "Ranh giới với Apologize (chỉ xin lỗi, không có giá trị bù đắp) học sinh khá hay nhầm — chưa có ví dụ phân biệt rõ trong batch này.",
      },
    ],
  },
];

const failedCluster = {
  id: "cluster-04-insufficient-input",
  status: "failed",
  rawInputSpan: "\"...và cả historic nữa...\"",
  reason:
    "Chỉ có 1 từ đơn lẻ (\"historic\") trong đoạn input được trích, không đủ ngữ cảnh cụm để tạo neo ngữ nghĩa đối chiếu (semantic anchor cần tối thiểu 2 từ dễ nhầm).",
  parseConfidence: "0.22 — dưới ngưỡng xử lý tối thiểu",
  suggestion:
    "Yêu cầu giáo viên bổ sung các từ dễ nhầm cùng nhóm với \"historic\" (vd. historical/classic/classical) rồi chạy lại batch.",
};

module.exports = { clusters, failedCluster };
