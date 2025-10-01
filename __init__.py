import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from nonebot import get_driver, on_command, on_keyword
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent, Message
from nonebot.params import CommandArg
from nonebot.typing import T_State

# 插件数据存储路径
DATA_PATH = Path(__file__).parent / "questions.json"

# 初始化数据结构
if not DATA_PATH.exists():
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "questions": [],
            "current_question": None
        }, f, ensure_ascii=False, indent=2)

# 加载数据
with open(DATA_PATH, "r", encoding="utf-8") as f:
    plugin_data = json.load(f)

# 当前题目ID
current_question_id: Optional[int] = plugin_data["current_question"]

# 保存数据到文件
def save_data():
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "questions": plugin_data["questions"],
            "current_question": current_question_id
        }, f, ensure_ascii=False, indent=2)

# 命令注册
next_question = on_command("a下一题")
switch_question = on_command("a切换题目")
ranking = on_command("a排行榜")
answer = on_keyword({"答"}, priority=5)

# 处理a下一题
@next_question.handle()
async def handle_next_question(event: GroupMessageEvent):
    global current_question_id
    
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
    save_data()
    await next_question.send(f"已切换到题目ID: {next_id}")

# 处理a切换题目
@switch_question.handle()
async def handle_switch_question(event: GroupMessageEvent, msg: Message = CommandArg()):
    global current_question_id
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
    save_data()
    await switch_question.send(f"已切换到题目ID: {target_id}")

# 处理a排行榜
@ranking.handle()
async def handle_ranking(event: GroupMessageEvent):
    if not plugin_data["questions"]:
        await ranking.send("暂无题目数据")
        return
    
    leaderboard = []
    for q in plugin_data["questions"]:
        if answered_by := q.get("answered_by"):
            leaderboard.append(f"题目{q['id']}: {answered_by['nickname']}({answered_by['user_id']})")
    
    if not leaderboard:
        await ranking.send("暂无答题记录")
        return
    
    await ranking.send("答题排行榜:\n" + "\n".join(leaderboard))

# 处理答题
@answer.handle()
async def handle_answer(event: MessageEvent, state: T_State):
    global current_question_id
    
    # 检查当前是否有题目
    if current_question_id is None:
        return
    
    # 获取用户答案
    user_answer = event.get_plaintext().replace("答", "", 1).strip()
    if not user_answer:
        return
    
    # 查找当前题目
    question = next((q for q in plugin_data["questions"] if q["id"] == current_question_id), None)
    if not question:
        return
    
    # 检查是否已有人答对
    if question.get("answered_by"):
        return
    
    # 检查答案是否正确
    if user_answer != question["answer"]:
        return
    
    # 记录答对者
    question["answered_by"] = {
        "nickname": event.sender.nickname or event.sender.card,
        "user_id": event.user_id
    }
    save_data()
    
    # 回复用户
    await answer.send(f"恭喜 {event.sender.nickname} 回答正确！")