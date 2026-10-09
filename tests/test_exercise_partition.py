import sys
from pathlib import Path
from docx import Document

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


def test_twenty_independent_questions_split_fourteen_six(tmp_path):
    p,s = make_source(tmp_path, ['%d. Solve independent item %d?'%(i,i) for i in range(1,21)])
    plan, evidence = partition_exercises(p, '1v1', s)
    assert len(plan.slots['immediate']) == 14
    assert len(plan.slots['final']) == 6
    assert plan.omitted_slots == ('knowledge',)
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
