from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent, Message
from nonebot.params import CommandArg
from nonebot.typing import T_State
from nonebot.permission import SUPERUSER
from nonebot import on_command, on_keyword
from .data_utils import *

next_question = on_command("a下一题")
switch_question = on_command("a切换题目")
question_answered = on_command("a题目作答情况")
ranking = on_command("a排行榜")
add_question = on_command("a添加题目", permission=SUPERUSER)
clear_questions = on_command("a清空题目", permission=SUPERUSER)
answer = on_keyword({"答"}, priority=5)

# 处理a下一题
def register_question_handlers(globals_dict):
    @next_question.handle()
    async def handle_next_question(event: GroupMessageEvent):
        global current_question_id, plugin_data
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
        question = next((q for q in plugin_data["questions"] if q["id"] == current_question_id), None)
        if question:
            await next_question.send(f"已切换到题目ID: {next_id}\n题目内容：{question['question']}")
        else:
            await next_question.send(f"已切换到题目ID: {next_id}")

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
        if not any(q["id"] == target_id for q in plugin_data["questions"]):
            await switch_question.send(f"题目ID {target_id} 不存在")
            return
        current_question_id = target_id
        plugin_data["current_question"] = current_question_id
        save_all()
        question = next((q for q in plugin_data["questions"] if q["id"] == current_question_id), None)
        if question:
            await switch_question.send(f"已切换到题目ID: {target_id}\n题目内容：{question['question']}")
        else:
            await switch_question.send(f"已切换到题目ID: {target_id}")

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

    @answer.handle()
    async def handle_answer(event: MessageEvent, state: T_State):
        global current_question_id, plugin_data
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
