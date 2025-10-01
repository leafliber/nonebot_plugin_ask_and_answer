import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from nonebot import get_driver, on_command, on_keyword
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent, Message
from nonebot.params import CommandArg
from nonebot.typing import T_State
from nonebot.permission import SUPERUSER

# 插件数据存储路径
DATA_PATH = "data/questions.json"

# 初始化数据结构
if not os.path.exists(DATA_PATH):
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
question_answered = on_command("a题目作答情况")
ranking = on_command("a排行榜")
add_question = on_command("a添加题目", permission=SUPERUSER)
clear_questions = on_command("a清空题目", permission=SUPERUSER)
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
    # 统计每个用户的答题数量
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
    
    # 转换为列表并按答题数量排序
    sorted_users = sorted(
        user_stats.items(),
        key=lambda x: x[1]["count"],
        reverse=True
    )
    
    # 获取所有用户数量
    total_users = len(sorted_users)
    
    # 构建排行榜消息
    leaderboard = []
    
    # 处理人数不足5人的情况
    if total_users < 5:
        # 显示所有用户
        for rank, (user_id, data) in enumerate(sorted_users, 1):
            leaderboard.append(f"{rank}. {data['nickname']} ({user_id}) - {data['count']}题")
    else:
        # 只取前5名
        top_users = sorted_users[:5]
        for rank, (user_id, data) in enumerate(top_users, 1):
            leaderboard.append(f"{rank}. {data['nickname']} ({user_id}) - {data['count']}题")
        
        # 添加总用户数信息
        leaderboard.append(f"\n共{total_users}位用户参与答题")
    
    await ranking.send("答题排行榜（按答题数量排序）:\n" + "\n".join(leaderboard))

# 处理添加题目
@add_question.handle()
async def handle_add_question(event: MessageEvent, msg: Message = CommandArg()):
    content = msg.extract_plain_text().strip()
    if not content:
        await add_question.send("请提供题目和答案，格式: a添加题目 问题|答案")
        return
    
    # 解析题目和答案
    parts = content.split("|", 1)
    if len(parts) < 2:
        await add_question.send("格式错误，请使用'|'分隔问题和答案")
        return
    
    question_text = parts[0].strip()
    answer_text = parts[1].strip()
    
    if not question_text or not answer_text:
        await add_question.send("问题和答案不能为空")
        return
    
    # 生成新题目ID
    new_id = max([q["id"] for q in plugin_data["questions"]], default=0) + 1
    
    # 添加新题目
    new_question = {
        "id": new_id,
        "question": question_text,
        "answer": answer_text
    }
    plugin_data["questions"].append(new_question)
    save_data()
    
    await add_question.send(f"添加成功！题目ID: {new_id}\n问题: {question_text}\n答案: {answer_text}")

@clear_questions.handle()
async def handle_clear_questions(event: MessageEvent):
    # 清空题目数据
    plugin_data["questions"] = []
    global current_question_id
    current_question_id = None
    save_data()
    
    await clear_questions.send("所有题目已清空！")

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