# V1.2 XML Finalization — Fixed Evaluation Set Audit

Audit date: 2026-10-07

## Frozen baseline

- Baseline input manifest: `C:\xml-uat\stage3-expansion\baseline_inputs.json`
- Frozen source files: 27 (X001–X027)
- Distinct topic identities after teacher/student/answer role deduplication: 13
- Incident pair: X005/X006, counted as one topic `九年级上学期物理期末复习(易错精选60题27大考点)`

The phrase “27 fixed raw corpus topics” is ambiguous in existing evidence: the frozen manifest has 27 source files but only 13 distinct topic identities after role variants are collapsed. This report preserves both counts instead of treating teacher/student role variants as extra topics.

## Additional raw topic selection

- Search roots: `C:\Users\Administrator\Desktop\工作\讲义生成器\训练文件`, `C:\xml-uat\c4-product-recovery\corpus`
- Deterministic source entries examined: 701
- Archive members seen: 988 in 254 ZIPs
- Distinct additional eligible DOCX topics selected: 20 of 20 requested
- Shortage: 0

Order follows the listed raw corpus roots, sorted root paths, ZIP member order, and depth-first nested ZIP traversal, matching the previous recovery script. Topic order is fixed by first eligible occurrence; role variants for a selected topic are recorded as members.

## Frozen 13 distinct topic identities (27 source files)

- 1.1 物质的变化和性质 第1课时(讲义) (X017,X018)
- 1.1 物质的变化和性质 第2课时(讲义) (X019,X020)
- 1.2 化学实验与科学探究(题型专练) (X021,X022,X023)
- 2.1 我们周围的空气 第1课时(讲义) (X024,X025)
- 2.2 氧气(讲义) (X026,X027)
- 专题02 电压 电阻&欧姆定律(期末复习讲义) (X001,X002)
- 专题04 电功率(期末专项训练) (X003,X004)
- 专题1.5 有理数的乘除(高效培优讲义)数学新教材沪科版七年级上册 (X011,X012)
- 专题1.6 有理数的乘方与近似数(高效培优讲义)数学新教材沪科版七年级上册 (X013,X014)
- 专题12.4 一次函数的实际应用(高效培优讲义)数学新教材沪科版八年级上册 (X015,X016)
- 九年级上学期物理期末复习(易错精选60题27大考点) (X005,X006)
- 第2节 分子动理论的初步知识(培优考点练) (X007,X008)
- 第3节 串联和并联 (培优考点练) (X009,X010)

## Additional selected topics

1. **专题05 二元一次方程组** — student_or_original_paper `db44bc6c0b85988def87a0bd4adc4f31d9fc344dcd5ad6839e52a0726e8f5d90` (专题05 二元一次方程组（原卷版）.docx), teacher_or_answer_rich `62139d6487958d0bab577e6e7be35d77dac65eb675fb2081b98838e273d35f6a` (专题05 二元一次方程组（解析版）.docx)
2. **专题10 新定义型答案** — student_or_original_paper `4191436e30005201fcb581a050fb4a888f882464cb6ceb07741ac2709ba84fe0` (专题10 新定义型答案（原卷版）.docx), teacher_or_answer_rich `d1884778c376a651bacf17b5cce348f332e8a18149822446e62059ea3b8b09b0` (专题10 新定义型答案（解析版）.docx)
3. **专题06 二元一次方程组的应用** — teacher_or_answer_rich `c781502d70a7839d44d5039419bdbf00e994b62eeb55d1fe486de5a91a2e363a` (专题06 二元一次方程组的应用（解析版）.docx), student_or_original_paper `0bd71d0822de32b74249584543c0137af1bf849a9e599194fae629c84d33f62e` (专题06 二元一次方程组的应用（原卷版）.docx)
4. **专题08 不等式与不等式组应用** — student_or_original_paper `ba2cbeb791422a8accca4e95cf9565e1aad5c19929100129e41a3de0fdf32281` (专题08 不等式与不等式组应用（原卷版）.docx), teacher_or_answer_rich `09e59e0f888ec0395be08ba5ecdbec62d8b1e02ad37640286b10da69ca3ca6fc` (专题08 不等式与不等式组应用（解析版）.docx)
5. **专题02 平行线模型和辅助线 专题专练【重难点培优:知识梳理+8大题型+压轴真题】2025-2026学年人教版数学七年级下册** — teacher_or_answer_rich `8639fd84bbee291b1bae7cd3c0290df028e4142ab656166eb611237addb5e476` (专题02 平行线模型和辅助线 专题专练【重难点培优：知识梳理+8大题型+压轴真题】2025-2026学年人教版数学七年级下册（解析版）.docx), student_or_original_paper `18abb7103ff821b7096557c16792758d48c3ccc551a611dc8550806e19b8c4bc` (专题02 平行线模型和辅助线 专题专练【重难点培优：知识梳理+8大题型+压轴真题】2025-2026学年人教版数学七年级下册（原卷版）.docx)
6. **专题07 不等式与不等式组** — teacher_or_answer_rich `c214a90b9ae519b27ad79a675683bddd7b8a803c1b2f69477e58e8b12a7fea1c` (专题07 不等式与不等式组（解析版）.docx), student_or_original_paper `03b98e25de5c3c8895f17e536de1b35466eb7bfa3e043d59e3fb9d9823a54ff7` (专题07 不等式与不等式组（原卷版）.docx)
7. **专题04 平面直角坐标系** — student_or_original_paper `a9b98d5d27f1d5484a1adb3db8e086760457b2535c35a6adf5e7d2e98e95f6c8` (专题04 平面直角坐标系（原卷版）.docx), teacher_or_answer_rich `7a2c1e13289c00cb48576c5a57089a763f465e6cfd6c81bc9c64e1205e8b686e` (专题04 平面直角坐标系（解析版）.docx)
8. **专题01 相交线与平行线中的几何综合 专题专练【重难点培优:知识梳理+7大题型+压轴真题】2025-2026学年人教版数学七年级下册** — teacher_or_answer_rich `3b0be92295c3ed587099987a90fd12be0fc3a6712fb46a09d67a3ba17763b379` (专题01 相交线与平行线中的几何综合 专题专练【重难点培优：知识梳理+7大题型+压轴真题】2025-2026学年人教版数学七年级下册(解析版）.docx), student_or_original_paper `9785aadc3bdb4ebafab8f62f2f8f7d4eea7427afa8d23dffb2e5b4b7ce0ed3c2` (专题01 相交线与平行线中的几何综合 专题专练【重难点培优：知识梳理+7大题型+压轴真题】2025-2026学年人教版数学七年级下册（原卷版）.docx)
9. **专题09 规律探索型** — teacher_or_answer_rich `ae0c39b370d7acc51a96463cbfd7f221f04037033e1515a4529a95664ae8b938` (专题09 规律探索型（解析版）.docx), student_or_original_paper `f4c2eda4c5c9d37a80e0d2c265cc02b290adf147deee0d12faaf9125ab54ac86` (专题09 规律探索型（原卷版）.docx)
10. **专题11 存在性问题** — student_or_original_paper `b56951ea6cf876d8742a00ac8ab62503c63a60ee0e22db2bafccdd537d333856` (专题11 存在性问题（原卷版）.docx), teacher_or_answer_rich `18c2ead455ca27d92f4f4eb4bad6b6bca91c5f18ccfc55c5dde356a8a8539ee3` (专题11 存在性问题（解析版）.docx)
11. **专题03 实数相关** — student_or_original_paper `156e69b6654630b51596f670da861c12ca8b3cfce2c7222d3f6059cedef841b5` (专题03 实数相关（原卷版）.docx), teacher_or_answer_rich `b92e1075e33e52b9aa4bf02723a400f6aae35c6de66170514779e6fca2918587` (专题03 实数相关（解析版）.docx)
12. **2026-2027年人教版物理九年级第十三章第二节 分子动理论的初步知识 (讲义)** — teacher_or_answer_rich `206c9b90b8d06d91905a75a5978c6c2d3825478030301e039f119d2f2ad314f2` (2026-2027年人教版物理九年级第十三章第二节 分子动理论的初步知识 （讲义）（解析版）.docx), student_or_original_paper `95169b0e507b5a959b8e5307daf5c725f25cd74056bbd61f185eb7c2a0f4213e` (2026-2027年人教版物理九年级第十三章第二节 分子动理论的初步知识 （讲义）（原卷版）.docx)
13. **15.2 电流和电路(讲义)2026-2027年人教版物理九年级全一册** — teacher_or_answer_rich `c4b4f3bb3b9730bca0701531af0ca429bc8977e6a4dd6f8047861e4239ce2746` (15.2 电流和电路（讲义）2026-2027年人教版物理九年级全一册（解析版） .docx), student_or_original_paper `94dce92abd5a11ad0b42034c8e95b2356153fdea8779461c93943ab5f7d055dd` (15.2 电流和电路（讲义）2026-2027年人教版物理九年级全一册（原卷版） .docx)
14. **15.4 电流的测量(讲义)2026-2027年人教版物理九年级全一册** — student_or_original_paper `5ff644bb5e3b1a359204cf01ee8a3a2ca526bbbbf0f82f8a0b64b86f605e453b` (15.4 电流的测量（讲义）2026-2027年人教版物理九年级全一册（原卷版）.docx), teacher_or_answer_rich `ed6573a7e00fac3fa7e757a6ff066483f82bdd366d16d35b9d2bb8bc53198062` (15.4 电流的测量（讲义）2026-2027年人教版物理九年级全一册（解析版）.docx)
15. **2026-2027年人教版物理九年级第十三章第三节 内能 (讲义)** — teacher_or_answer_rich `2ba5500c188081932f1d676ab35aaf600a2d40cf9bb430ad80fbebe3f5353cec` (2026-2027年人教版物理九年级第十三章第三节 内能 （讲义）（解析版） .docx), student_or_original_paper `6d06f858bf7a4933d82cb4e142905f115529cd95eeabab2a9377bfb14d3e70d6` (2026-2027年人教版物理九年级第十三章第三节 内能 （讲义）（原卷版） .docx)
16. **15.3 串联电路和并联电路(讲义)2026-2027年人教版物理九年级全一册** — teacher_or_answer_rich `a12c44dd1da47c09a3961e1d7d7e9bf537f5341d076529db8bd80662a4ee5211` (15.3 串联电路和并联电路（讲义）2026-2027年人教版物理九年级全一册（解析版）.docx), student_or_original_paper `34204059d17a0329806c2abf3941f1cd3d88583c75d89dfb841a89b98d9ab56e` (15.3 串联电路和并联电路（讲义）2026-2027年人教版物理九年级全一册（原卷版）.docx)
17. **2026-2027年人教版物理九年级第十三章第一节 热量 比热容 (讲义)** — teacher_or_answer_rich `b5e217e9a2311d398af5be97446b86b84992bd541683f83c7773cde22885419e` (2026-2027年人教版物理九年级第十三章第一节 热量 比热容 （讲义）（解析版）.docx), student_or_original_paper `755f20a000e5bfa9638bc279318fc0753d54019096e250b959bd0522b4dc1b71` (2026-2027年人教版物理九年级第十三章第一节 热量 比热容 （讲义）（原卷版）.docx)
18. **13.3 热机效率(讲义)2026-2027年人教版物理九年级全一册** — student_or_original_paper `781e2b1a04ac28096d05d9c4cd9cf1bfa2f13f999fae3c2a247f345651bb2e16` (13.3 热机效率（讲义）2026-2027年人教版物理九年级全一册（原卷版）.docx), teacher_or_answer_rich `3674e8a29fa2f4d1cbc6d295aa06ca64bab4e51e53128d703e1b23c58d28f921` (13.3 热机效率（讲义）2026-2027年人教版物理九年级全一册（解析版）.docx)
19. **15.1 两种电荷(讲义)2026-2027年人教版物理九年级全一册** — teacher_or_answer_rich `df2192ef89930f9d23ffa279ca0796bc9b844a3af67a34c7ed7998913fdb822b` (15.1 两种电荷（讲义）2026-2027年人教版物理九年级全一册（解析版）.docx), student_or_original_paper `b3aeeb883c8b1a7357ea0e66071cec4d311c7b7343933ee4099cc46d6c66ac24` (15.1 两种电荷（讲义）2026-2027年人教版物理九年级全一册（原卷版）.docx)
20. **2026-2027年人教版物理九年级第十四章第二节 热机 (讲义)** — student_or_original_paper `940e6b3853893a1dd89615754a8fbdf916021f4ec772cddb217753bbfd2614b3` (2026-2027年人教版物理九年级第十四章第二节 热机 （讲义）（原卷版）  .docx), teacher_or_answer_rich `1318a6c140e1fb110066596a454885e345caa523194f6372031d719605bae3ad` (2026-2027年人教版物理九年级第十四章第二节 热机 （讲义）（解析版）  .docx)

## Blockers and limits

- Archive traversal errors: 2; details are in the frozen manifest.
- Existing extraction copies were used read-only; original sources were not altered.
- No XML renderer was run, so this audit makes no XML success-rate claim.
- Old route/output scans are stale relative to the current commit and are not interpreted as current candidate results.
