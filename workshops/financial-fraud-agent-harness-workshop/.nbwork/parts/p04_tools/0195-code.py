_question = "the agent keeps querying a column that does not exist; how do I find the real table and column names?"
print(_question, "\n")
for _s in json.loads(tool_list_skills(_question, k=3)):
    print(f"{_s['name']}  ({_s['category']})\n   {_s['description'][:160].strip()}...\n")
