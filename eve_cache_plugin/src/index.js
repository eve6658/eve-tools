/**
 * Eve Cache Optimizer Plugin
 * 
 * Hooks (via api.on):
 *   before_prompt_build — Canonicalization + L2 cache check + Context retrieval
 *   before_tool_call    — Tool result cache check
 *   after_tool_call     — Store tool result in cache
 *   agent_end           — Log metrics
 * 
 * Integrates with Python backend:
 *   ../cache_orchestrator.py
 */

const { execSync } = require('child_process');
const path = require('path');

const PLUGIN_DIR = path.resolve(__dirname, '..');
const ORCHESTRATOR = path.join(PLUGIN_DIR, 'cache_orchestrator.py');
const PYTHON = 'python3';

function runOrchestrator(args) {
  try {
    const result = execSync(`${PYTHON} ${ORCHESTRATOR} ${args}`, {
      timeout: 5000,
      encoding: 'utf-8',
      env: { ...process.env, PYTHONPATH: PLUGIN_DIR }
    });
    return JSON.parse(result.trim());
  } catch (e) {
    return { error: e.message?.slice(0, 200) };
  }
}

module.exports = {
  id: 'eve-cache',
  name: 'Eve Cache Optimizer',

  register(api) {
    const config = api.pluginConfig ?? {};
    const enabled = config.enabled !== false;
    const logLevel = config.logLevel ?? 'info';
    const log = (...args) => {
      if (logLevel !== 'off') console.log('[eve-cache]', ...args);
    };

    if (!enabled) {
      log('Disabled by config');
      return;
    }

    log('Registering hooks...');

    // ── Phase 1+2+4: before_prompt_build ──────────────
    // Can inject: prependContext, appendSystemContext, systemPrompt
    api.on('before_prompt_build', async (event) => {
      try {
        const userInput = event?.userInput ?? '';
        if (!userInput) return {};

        const result = runOrchestrator(
          `before_prompt "${userInput.replace(/"/g, '\\"')}" default full`
        );

        if (result.error) {
          log('before_prompt error:', result.error);
          return {};
        }

        // Cache hit — return cached response
        if (result.cache === 'L2_HIT' && result.response) {
          log(`L2 HIT key=${result.key?.slice(0, 12)}... saved=${result.tokens_saved} tokens`);
          return { cachedResponse: result.response };
        }

        // Miss — inject retrieved context
                        const res = {};
        if (result.context) {
          const blocks = result.context_blocks ?? 0;
          log(`MISS intent=${result.canonical?.intent} context_blocks=${blocks}`);
          res.appendSystemContext = `\n[Cache Context: ${blocks} blocks]\n${result.context}`;
                        } else {
          log(`MISS intent=${result.canonical?.intent} no_context`);
                        }

        return res;
      } catch (e) {
        log('before_prompt_build exception:', e.message);
        return {};
      }
    });

    // ── Phase 3: before_tool_call ─────────────────────
    api.on('before_tool_call', async (event) => {
      try {
        const toolName = event?.toolName ?? '';
        const argsJson = JSON.stringify(event?.args ?? {});

        const result = runOrchestrator(
          `before_tool "${toolName}" '${argsJson.replace(/'/g, "'\\''")}'`
        );

        if (result.error) return {};
        if (result.cache === 'TOOL_HIT') {
          log(`TOOL HIT tool=${toolName} key=${result.key?.slice(0, 12)}...`);
          return { cachedResult: result.result };
        }
        return {};
      } catch (e) {
        return {};
      }
    });

    // ── Phase 3: after_tool_call ──────────────────────
    api.on('after_tool_call', async (event) => {
      try {
        const toolName = event?.toolName ?? '';
        const argsJson = JSON.stringify(event?.args ?? {});
        const resultText = typeof event?.result === 'string'
          ? event.result.slice(0, 1000)
          : JSON.stringify(event?.result ?? {}).slice(0, 1000);

        runOrchestrator(
          `after_tool "${toolName}" '${argsJson.replace(/'/g, "'\\''")}' "${resultText.replace(/"/g, '\\"')}"`
        );
      } catch (e) {
        // silent
      }
      return {};
    });

    // ── Phase 5: agent_end ────────────────────────────
    api.on('agent_end', async (event) => {
      try {
        const metrics = {
          tokens: event?.usage?.totalTokens ?? 0,
          latency_ms: event?.latencyMs ?? 0
        };

        const result = runOrchestrator(
          `agent_end '${JSON.stringify(metrics)}'`
        );

        if (logLevel === 'debug' && !result.error) {
          log(`turn=${result.turn} prompt_hit=${result.prompt_hit_rate} tool_hit=${result.tool_hit_rate} saved=${result.tokens_saved}`);
        }
      } catch (e) {
        // silent
      }
      return {};
    });

    log('✅ Hooks registered: before_prompt_build, before_tool_call, after_tool_call, agent_end');
  }
};
