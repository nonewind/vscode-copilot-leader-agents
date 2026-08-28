# References

Authoritative references used by this project:

- VS Code custom agents: https://code.visualstudio.com/docs/agent-customization/custom-agents
- VS Code subagents: https://code.visualstudio.com/docs/agents/run/subagents
- VS Code language models and reasoning controls: https://code.visualstudio.com/docs/agent-customization/language-models
- VS Code Agent Skills: https://code.visualstudio.com/docs/agent-customization/agent-skills
- VS Code agent hooks: https://code.visualstudio.com/docs/agent-customization/hooks
- VS Code AI settings: https://code.visualstudio.com/docs/agents/reference/ai-settings
- GCMP Marketplace page: https://marketplace.visualstudio.com/items?itemName=vicanent.gcmp
- GCMP Zhipu model catalog: https://github.com/VicBilibily/GCMP/blob/main/src/providers/config/zhipu.json

Verified on 2026-08-28. The current GCMP Zhipu catalog declares `id: glm-5.3-flash` with display name `GLM-5.3-Flash (CodingPlan)`; this project uses its VS Code selector route `gcmp.zhipu:::glm-5.3-flash`. The VS Code references document isolated, stateless subagent invocations and model routing, but do not expose a separate reasoning-effort field for this `.agent.md`/`runSubagent` workflow. Update GCMP before installation if its local model selector does not list the model.
