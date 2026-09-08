from agent_reasoning.agents.base import BaseAgent
from agent_reasoning.visualization.models import StreamEvent, SubTask, TaskStatus


class DecomposedAgent(BaseAgent):
    def __init__(self, model="gemma3:270m", **kwargs):
        super().__init__(model, **kwargs)
        self.name = "DecomposedAgent"
        self.color = "red"

    def run(self, query):
        response = ""
        for chunk in self.stream(query):
            response += chunk
        return response

    def stream(self, query):
        """Yield text chunks for terminal streaming."""
        last_task_result_length = {}  # Track result length per task to yield only new content

        for event in self.stream_structured(query):
            if event.event_type == "text":
                yield event.data
            elif event.event_type == "chunk":
                # Direct chunk streaming from sub-task processing
                yield event.data
            elif event.event_type == "task":
                task = event.data
                if task.status == TaskStatus.RUNNING and not event.is_update:
                    yield f"\n**Solving sub-task {task.id}:** `{task.description}`\n"
                    last_task_result_length[task.id] = 0
                elif task.status == TaskStatus.RUNNING and event.is_update:
                    # Stream incremental result updates
                    if task.result:
                        prev_len = last_task_result_length.get(task.id, 0)
                        new_content = task.result[prev_len:]
                        if new_content:
                            yield new_content
                            last_task_result_length[task.id] = len(task.result)
                elif task.status == TaskStatus.COMPLETED and not event.is_update:
                    yield f"\n✅ Sub-task {task.id} completed.\n"

    def stream_structured(self, query):
        """Structured event streaming for visualization."""
        yield StreamEvent(event_type="query", data=query)
        yield StreamEvent(event_type="text", data=f"Processing query by decomposing: {query}\n")

        # 1. Decompose
        yield StreamEvent(event_type="text", data="\n**Decomposing the problem...**\n")
        decomposition_prompt = f"Break down the following complex problem into a numbered list of simple sub-tasks.\nProblem: {query}\nProvide only the list."

        yield StreamEvent(event_type="text", data="\n### Sub-tasks Plan:\n")
        sub_tasks_text = ""
        for chunk in self.client.generate(decomposition_prompt):
            sub_tasks_text += chunk
            yield StreamEvent(event_type="text", data=chunk)  # Stream decomposition in real-time

        yield StreamEvent(event_type="text", data="\n")

        # Parse sub-tasks
        lines = sub_tasks_text.split("\n")
        tasks = []
        task_id = 0
        for line in lines:
            line = line.strip()
            if not line:
                continue
            task_id += 1
            task = SubTask(id=task_id, description=line, status=TaskStatus.PENDING)
            tasks.append(task)
            yield StreamEvent(event_type="task", data=task)

        # 2. Execute Sub-tasks
        context = ""

        for task in tasks:
            # Mark as running
            task.status = TaskStatus.RUNNING
            yield StreamEvent(event_type="task", data=task, is_update=True)

            # Solve with context
            solve_prompt = f"Context so far:\n{context}\n\nCurrent Task: {task.description}\nSolve this task efficiently."

            task_solution = ""
            chunks_received = 0
            for chunk in self.client.generate(solve_prompt):
                task_solution += chunk
                chunks_received += 1
                # Update progress estimate
                task.progress = min(0.9, chunks_received * 0.1)
                task.result = task_solution
                yield StreamEvent(event_type="task", data=task, is_update=True)

            # Mark as completed
            task.status = TaskStatus.COMPLETED
            task.progress = 1.0
            task.result = task_solution
            yield StreamEvent(event_type="task", data=task, is_update=True)

            context += f"Task: {task.description}\nResult: {task_solution}\n"

        # 3. Synthesize
        yield StreamEvent(event_type="text", data="\n**Synthesizing final answer...**\n")
        synthesis_prompt = f"Original Query: {query}\n\nCompleted Sub-tasks results:\n{context}\n\nProvide the final comprehensive answer."

        yield StreamEvent(event_type="text", data="### Final Answer:\n")
        final_response = ""
        for chunk in self.client.generate(synthesis_prompt):
            final_response += chunk
            yield StreamEvent(event_type="text", data=chunk)

        yield StreamEvent(event_type="final", data=final_response)
