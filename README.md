# Travelly AI-Agent

AI-Agent for trip planning with many tools.


## Agents

### Root Agent

The main agent that routes tasks to subagents. Also this agent uses tools for save user`s interests in memory and 
get this info from memory.

### Flight Agent

Agent that searches flights and ticket prices using `fli` (mcp) and `travel-search-ru` (api) tools

### Hotel Agent



### Activity agent

Agent use web searcher `tavily` to get info about activities, food-places, etc. in requested city. 


## Tools

TODO


## Memory

For memory this system uses `mem0` tool and included in `google-adk` session memory.



## How to use?

To run this agent you need to have next API keys:

1. GOOGLE_API_KEY - for LLM-api
2. MEM0_API_KEY - for mem0-api 
3. GOOGLE_GENAI_USE_VERTEXAI = false - only use ai.studio API
4. TAVILY_API_KEY - web searcher

Next you need to enter this command in bash in order to apply envs:

`set -a; source travelly/.env; set +a`

Next you need to enter this command to run agent web-interface: 

`adk web`