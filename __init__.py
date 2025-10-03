import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from nonebot import get_driver, on_command, on_keyword
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent, Message
from nonebot.params import CommandArg
from nonebot.typing import T_State
from nonebot.permission import SUPERUSER

# 多题库支持
DATA_DIR = "data"
META_PATH = os.path.join(DATA_DIR, "meta.json")  # 存储当前题库名

def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def get_question_bank_path(bank_name: str) -> str:
    return os.path.join(DATA_DIR, f"{bank_name}.json")

def load_meta():
    if not os.path.exists(META_PATH):
        with open(META_PATH, "w", encoding="utf-8") as f:
            json.dump({"current_bank": "default"}, f)
    with open(META_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_meta(meta):
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

def load_bank(bank_name: str):
    path = get_question_bank_path(bank_name)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"questions": [], "current_question": None}, f, ensure_ascii=False, indent=2)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_bank(bank_name: str, data):
    path = get_question_bank_path(bank_name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def list_banks() -> List[str]:
    ensure_data_dir()
    return [f[:-5] for f in os.listdir(DATA_DIR) if f.endswith('.json') and f != 'meta.json']

ensure_data_dir()
meta = load_meta()
current_bank = meta.get("current_bank", "default")
plugin_data = load_bank(current_bank)
current_question_id: Optional[int] = plugin_data["current_question"]

def save_all():
    save_bank(current_bank, plugin_data)
    meta["current_bank"] = current_bank
    save_meta(meta)


# 命令注册
next_question = on_command("a下一题")
switch_question = on_command("a切换题目")
question_answered = on_command("a题目作答情况")
ranking = on_command("a排行榜")
add_question = on_command("a添加题目", permission=SUPERUSER)
clear_questions = on_command("a清空题目", permission=SUPERUSER)
answer = on_keyword({"答"}, priority=5)
list_banks_cmd = on_command("a题库列表", permission=SUPERUSER)
switch_bank_cmd = on_command("a切换题库", permission=SUPERUSER)
create_bank_cmd = on_command("a新建题库", permission=SUPERUSER)
delete_bank_cmd = on_command("a删除题库", permission=SUPERUSER)

# 处理a下一题
@next_question.handle()
async def handle_next_question(event: GroupMessageEvent):
    global current_question_id, plugin_data
    # 找到下一个未回答的问题
    next_id = None
    for q in plugin_data["questions"]:
        if q["id"] > (current_question_id or -1) and not q.get("answered_by"):
            next_id = q["id"]
            break
    if next_id is None:
        await next_question.send("没有更多题目了")
        return
    current_question_id = next_id
    plugin_data["current_question"] = current_question_id
    save_all()
    await next_question.send(f"已切换到题目ID: {next_id}")

# 处理a切换题目
@switch_question.handle()
async def handle_switch_question(event: GroupMessageEvent, msg: Message = CommandArg()):
    global current_question_id, plugin_data
    arg = msg.extract_plain_text().strip()
    if not arg:
        await switch_question.send("请输入题目ID")
        return
    try:
        target_id = int(arg)
    except ValueError:
        await switch_question.send("请输入有效的题目ID")
        return
    # 检查题目是否存在
    if not any(q["id"] == target_id for q in plugin_data["questions"]):
        await switch_question.send(f"题目ID {target_id} 不存在")
        return
    current_question_id = target_id
    plugin_data["current_question"] = current_question_id
    save_all()
    await switch_question.send(f"已切换到题目ID: {target_id}")

# 处理a题目作答情况
@question_answered.handle()
async def handle_question_answered(event: GroupMessageEvent):
    if not plugin_data["questions"]:
        await question_answered.send("暂无题目数据")
        return
    leaderboard = []
    for q in plugin_data["questions"]:
        if answered_by := q.get("answered_by"):
            leaderboard.append(f"题目{q['id']}: {answered_by['nickname']}({answered_by['user_id']})")
    if not leaderboard:
        await question_answered.send("暂无答题记录")
        return
    await question_answered.send("答题排行榜:\n" + "\n".join(leaderboard))

# 处理a排行榜（按用户答题数量排序）
@ranking.handle()
async def handle_ranking(event: GroupMessageEvent):
    user_stats = {}
    for q in plugin_data["questions"]:
        if answered_by := q.get("answered_by"):
            user_id = answered_by["user_id"]
            nickname = answered_by["nickname"]
            if user_id not in user_stats:
                user_stats[user_id] = {
                    "nickname": nickname,
                    "count": 0
                }
            user_stats[user_id]["count"] += 1
    if not user_stats:
        await ranking.send("暂无答题记录")
        return
    sorted_users = sorted(
        user_stats.items(),
        key=lambda x: x[1]["count"],
        reverse=True
    )
    total_users = len(sorted_users)
    leaderboard = []
    if total_users < 5:
        for rank, (user_id, data) in enumerate(sorted_users, 1):
            leaderboard.append(f"{rank}. {data['nickname']} ({user_id}) - {data['count']}题")
    else:
        top_users = sorted_users[:5]
        for rank, (user_id, data) in enumerate(top_users, 1):
            leaderboard.append(f"{rank}. {data['nickname']} ({user_id}) - {data['count']}题")
        leaderboard.append(f"\n共{total_users}位用户参与答题")
    await ranking.send("答题排行榜（按答题数量排序）:\n" + "\n".join(leaderboard))

# 处理添加题目
@add_question.handle()
async def handle_add_question(event: MessageEvent, msg: Message = CommandArg()):
    global plugin_data
    content = msg.extract_plain_text().strip()
    if not content:
        await add_question.send("请提供题目和答案，格式: a添加题目 问题|答案")
        return
    parts = content.split("|", 1)
    if len(parts) < 2:
        await add_question.send("格式错误，请使用'|'分隔问题和答案")
        return
    question_text = parts[0].strip()
    answer_text = parts[1].strip()
    if not question_text or not answer_text:
        await add_question.send("问题和答案不能为空")
        return
    new_id = max([q["id"] for q in plugin_data["questions"]], default=0) + 1
    new_question = {
        "id": new_id,
        "question": question_text,
        "answer": answer_text
    }
    plugin_data["questions"].append(new_question)
    save_all()
    await add_question.send(f"添加成功！题目ID: {new_id}\n问题: {question_text}\n答案: {answer_text}")

@clear_questions.handle()
async def handle_clear_questions(event: MessageEvent):
    global current_question_id, plugin_data
    plugin_data["questions"] = []
    current_question_id = None
    plugin_data["current_question"] = None
    save_all()
    await clear_questions.send("所有题目已清空！")

# 处理答题
@answer.handle()
async def handle_answer(event: MessageEvent, state: T_State):
    global current_question_id, plugin_data
    # 检查当前是否有题目
    if current_question_id is None:
        return
    user_answer = event.get_plaintext().replace("答", "", 1).strip()
    if not user_answer:
        return
    question = next((q for q in plugin_data["questions"] if q["id"] == current_question_id), None)
    if not question:
        return
    if question.get("answered_by"):
        return
    if user_answer != question["answer"]:
        return
    question["answered_by"] = {
        "nickname": event.sender.nickname or event.sender.card,
        "user_id": event.user_id
    }
    save_all()
    await answer.send(f"恭喜 {event.sender.nickname} 回答正确！")

# 题库管理命令实现
@list_banks_cmd.handle()
async def handle_list_banks(event: MessageEvent):
    banks = list_banks()
    await list_banks_cmd.send("当前题库列表：\n" + "\n".join(banks))

@switch_bank_cmd.handle()
async def handle_switch_bank(event: MessageEvent, msg: Message = CommandArg()):
    global current_bank, plugin_data, current_question_id
    bank_name = msg.extract_plain_text().strip()
    if not bank_name:
        await switch_bank_cmd.send("请提供题库名")
        return
    if bank_name not in list_banks():
        await switch_bank_cmd.send(f"题库 {bank_name} 不存在")
        return
    current_bank = bank_name
    plugin_data = load_bank(current_bank)
    current_question_id = plugin_data["current_question"]
    save_all()
    await switch_bank_cmd.send(f"已切换到题库：{bank_name}")

@create_bank_cmd.handle()
async def handle_create_bank(event: MessageEvent, msg: Message = CommandArg()):
    bank_name = msg.extract_plain_text().strip()
    if not bank_name:
        await create_bank_cmd.send("请提供新题库名")
        return
    if bank_name in list_banks():
        await create_bank_cmd.send("题库已存在")
        return
    save_bank(bank_name, {"questions": [], "current_question": None})
    await create_bank_cmd.send(f"题库 {bank_name} 创建成功！")

@delete_bank_cmd.handle()
async def handle_delete_bank(event: MessageEvent, msg: Message = CommandArg()):
    global current_bank, plugin_data, current_question_id
    bank_name = msg.extract_plain_text().strip()
    if not bank_name:
        await delete_bank_cmd.send("请提供要删除的题库名")
        return
    if bank_name not in list_banks():
        await delete_bank_cmd.send("题库不存在")
        return
    if bank_name == current_bank:
        await delete_bank_cmd.send("不能删除当前正在使用的题库，请先切换到其他题库")
        return
    path = get_question_bank_path(bank_name)
    os.remove(path)
    await delete_bank_cmd.send(f"题库 {bank_name} 已删除")