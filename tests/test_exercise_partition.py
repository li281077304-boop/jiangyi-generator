import sys
from pathlib import Path
from docx import Document
from docx.oxml import OxmlElement
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'v1.2-xml-experiment/res/app'))
from exercise_partition import partition_exercises
from semantic_facade import analyze_source


def make_source(tmp_path, lines):
    p = tmp_path / 'source.docx'
    d = Document()
    for line in lines:
        d.add_paragraph(line)
    d.save(p)
    return p, analyze_source(p)


def test_twenty_independent_questions_reserve_one_example_then_split_thirteen_six(tmp_path):
    p,s = make_source(tmp_path, ['%d. Solve independent item %d?'%(i,i) for i in range(1,21)])
    plan, evidence = partition_exercises(p, '1v1', s)
    assert len(plan.slots['knowledge']) == 1
    assert len(plan.slots['immediate']) == 13
    assert len(plan.slots['final']) == 6
    assert plan.omitted_slots == ()
    assert evidence['knowledge_content_mode'] == 'SOURCE_EXAMPLE'
    ids = [span.start for spans in plan.slots.values() for span in spans]
    assert len(set(ids)) == len(ids) == 20


def test_passages_questions_and_inline_answers_stay_whole(tmp_path):
    lines=[]
    for n in range(1,6):
        lines += ['Passage %d'%n, 'A long shared reading material.', '1. A. alpha B. beta',
                  '2. A. gamma B. delta', '参考答案', '1. A', '2. B']
    p,s = make_source(tmp_path, lines)
    plan, evidence = partition_exercises(p, 'class', s)
    routes = {r['source_index']:r['destination_slot'] for r in plan.block_records}
    for start in range(0,len(lines),7):
        assert len({routes[i] for i in range(start,start+7)}) == 1
    assert plan.slots['immediate'] and plan.slots['final']


def test_concentrated_answers_are_not_counted_as_new_questions(tmp_path):
    p,s = make_source(tmp_path, ['%d. Independent problem?'%i for i in range(1,21)]
                      + ['参考答案'] + ['%d. A'%i for i in range(1,21)])
    plan,e = partition_exercises(p, '1v1', s)
    assert len(e['groups']) == 20
    routes = {r['source_index']:r['destination_slot'] for r in plan.block_records}
    assert all(routes[i]=='final' for i in range(20,41))


def test_real_knowledge_is_preserved_without_using_exercises_as_knowledge(tmp_path):
    p,s = make_source(tmp_path, ['基础·知识梳理','A reliable explanation.','1. Method detail',
                      '拔高·分层集训'] + ['%d. Exercise?'%i for i in range(1,11)])
    plan,e = partition_exercises(p,'1v1',s)
    assert {span.start for span in plan.slots['knowledge']} == {'b0','b1','b2'}
    assert plan.slots['immediate'] and plan.slots['final']


def test_explicit_practice_column_ends_knowledge_context_and_keeps_answers(tmp_path):
    lines = ['知识点1 副词的分类', '真实知识讲解。', '优题精练·专题实战通关']
    for i in range(1, 16):
        lines += [f'{i}. Exercise {i}?', f'【答案】answer {i}', f'【解析】explanation {i}']
    p, snapshot = make_source(tmp_path, lines)
    plan, evidence = partition_exercises(p, '1v1', snapshot)
    assert len(evidence['groups']) == 15
    routes = {r['source_index']: r['destination_slot'] for r in plan.block_records}
    assert routes[0] == routes[1] == 'knowledge'
    for start in range(3, len(lines), 3):
        assert len({routes[start], routes[start + 1], routes[start + 2]}) == 1
    assert routes[2] == routes[3] == 'immediate'
    assert plan.slots['knowledge'] and plan.slots['immediate'] and plan.slots['final']


def test_source_example_keeps_entire_passage_and_its_answers(tmp_path):
    lines = []
    for n in range(1, 6):
        lines += [f'Passage {n}', 'A complete shared passage.', '1. First question?',
                  '2. Second question?', '参考答案', '1. A', '2. B']
    path, snapshot = make_source(tmp_path, lines)
    plan, evidence = partition_exercises(path, '1v1', snapshot)
    assert evidence['knowledge_content_mode'] == 'SOURCE_EXAMPLE'
    assert {span.start for span in plan.slots['knowledge']} == {f'b{i}' for i in range(7)}
    ids = [span.start for spans in plan.slots.values() for span in spans]
    assert len(ids) == len(set(ids)) == len(lines)


def test_two_groups_cannot_fake_three_filled_slots(tmp_path):
    from slot_router import SlotRoutingError
    import pytest
    path, snapshot = make_source(tmp_path, ['1. Independent question?', '2. Another question?'])
    with pytest.raises(SlotRoutingError) as failure:
        partition_exercises(path, '1v1', snapshot)
    assert failure.value.reason_code == 'INSUFFICIENT_COMPLETE_GROUPS_FOR_THREE_SLOTS'


@pytest.mark.parametrize('calculation', ['0.3A×30Ω+0.3A6V+U，', '12.5×2=25', '2.75V', '0．3×2=0．6'])
def test_decimal_calculation_is_neither_boundary_nor_question_weight(tmp_path, calculation):
    lines = ['1. 2x + 3 = 7，求x。', '【解答】先列方程。', calculation,
             '2. Second independent question?', '3. Third question?', '4. Fourth question?']
    path, snapshot = make_source(tmp_path, lines)
    plan, evidence = partition_exercises(path, '1v1', snapshot)
    assert [g['start'] for g in evidence['groups']] == [0, 3, 4, 5]
    assert [g['weight'] for g in evidence['groups']] == [1, 1, 1, 1]
    assert [number for number, _slot in plan.training_question_routes] == [1, 2, 3, 4]
    routes = {r['source_index']: r['destination_slot'] for r in plan.block_records}
    assert routes[0] == routes[1] == routes[2]


def test_formula_only_inline_answer_does_not_consume_following_questions(tmp_path):
    path = tmp_path / 'math-answers.docx'
    document = Document()
    for number in range(1, 7):
        document.add_paragraph(f'{number}. A separate numeric problem?')
        answer = document.add_paragraph('【答案】')
        math = OxmlElement('m:oMath')
        run = OxmlElement('m:r')
        value = OxmlElement('m:t')
        value.text = str(number)
        run.append(value); math.append(run); answer._p.append(math)
        document.add_paragraph('【分析】这是当前题的解答。')
    document.save(path)
    snapshot = analyze_source(path)
    assert snapshot.document.blocks[1].text == '【答案】'
    assert snapshot.document.blocks[1].math_count == 1
    plan, evidence = partition_exercises(path, 'class', snapshot)
    assert [g['start'] for g in evidence['groups']] == list(range(0, 18, 3))
    routes = {r['source_index']: r['destination_slot'] for r in plan.block_records}
    for start in range(0, 18, 3):
        assert len({routes[start], routes[start + 1], routes[start + 2]}) == 1


@pytest.mark.parametrize('marker', ['【答案】', '[答案]', '【解析】'])
def test_bare_marker_without_inline_content_fails_closed(tmp_path, marker):
    from slot_router import SlotRoutingError
    path, snapshot = make_source(tmp_path, ['1. First question?', '2. Second question?',
        '3. Third question?', marker, '1. A', '2. B', '3. C'])
    with pytest.raises(SlotRoutingError) as failure:
        partition_exercises(path, '1v1', snapshot)
    assert failure.value.reason_code == 'AMBIGUOUS_ANSWER_HEADING'


def test_explicit_bracketed_global_reference_answers_remain_global(tmp_path):
    lines = [f'{i}. Independent question?' for i in range(1, 7)]
    lines += ['【参考答案】'] + [f'{i}. A' for i in range(1, 7)]
    path, snapshot = make_source(tmp_path, lines)
    _plan, evidence = partition_exercises(path, '1v1', snapshot)
    assert [g['start'] for g in evidence['groups']] == list(range(6))


def test_unseparated_numeric_first_stem_is_not_silently_lost(tmp_path):
    from slot_router import SlotRoutingError
    path, snapshot = make_source(tmp_path, ['1.2x+3=7，求x。',
        '2. Another question?', '3. Third question?', '4. Fourth question?'])
    with pytest.raises(SlotRoutingError) as failure:
        partition_exercises(path, '1v1', snapshot)
    assert failure.value.reason_code == 'AMBIGUOUS_QUESTION_NUMBER'


def test_ole_only_inline_answer_uses_structural_content_evidence(tmp_path):
    # Controlled parsed snapshot: this test targets partitioning, not the DOCX
    # OLE parser or renderer. No invalid embedded object is written to a DOCX.
    lines = []
    for number in range(1, 5):
        lines.extend([f'{number}. Independent problem?', '【答案】', '【分析】当前题解答。'])
    path, snapshot = make_source(tmp_path, lines)
    for index in range(1, len(lines), 3):
        block = snapshot.document.blocks[index]
        assert block.math_count == 0
        block.oles = ['controlled-ole-answer-evidence']
    plan, evidence = partition_exercises(path, 'class', snapshot)
    assert [g['start'] for g in evidence['groups']] == [0, 3, 6, 9]
    routes = {r['source_index']: r['destination_slot'] for r in plan.block_records}
    for start in range(0, len(lines), 3):
        assert routes[start] == routes[start + 1] == routes[start + 2]
