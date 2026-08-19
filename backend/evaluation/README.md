# Evaluation Json Files

## 1. eval_questions.json

```js
  {
    "question": "What does alarm AL088_CAP_CHECK_DEVICE_ALARM mean and how do I resolve it?",
    "expected_agent": "diagnosis"
  }
```

- Question + which agent should handle it. Made by pulling real orders/alarms from the DB and templating a question per row, with the agent label assigned by a fixed rule (order→commercial, alarm→diagnosis, etc.). 

- Purpose: test routing.


## 2. multi_agent_questions.json

```js
  {
    "question": "Is there an open order for this machine, and why does it keep raising the same alarm?",
    "expected_agents": ["commercial", "diagnosis"]
  },
```

- Question + which multiple agents it needs . Hand-written with the help of AI.

- Purpose: test whether the planner combines specialists.



## 3. rag_questions.json

```js
 {
    "question": "What are the four specific intervals of working hours defined for maintenance schedules between section 11.5.1.4 and 11.5.1.8?",
    "chunk_id": 2777,
    "machine_serial": "17478",
    "source_file": "17478_manual_EN.pdf",
    "page": 8
  },
```

- Question + which manual chunk it came from. Qwen read a real chunk and wrote a question about it; the chunk itself is the known-correct source.

- Purpose: test retrieval (does search find that chunk).

## 4. answer_questions.json

```js
 {
    "question": "What is the status of order ORD-2026-0006?",
    "machine_serial": "15610",
    "reference_fact": "Order ORD-2026-0006 has status 'Delivered' and shipment status 'Delivered'."
  },
```
- Question + a true fact (plain sentence built from real DB fields, no LLM). 

- Purpose: test final answer quality via judge does the generated answer match the real fact




