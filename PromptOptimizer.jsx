import { useState, useCallback, useRef, useEffect } from "react";

// ─── Design Tokens ────────────────────────────────────────────────
const C = {
  bg:"#07090d", surface:"#0d1018", panel:"#12151f", panelHi:"#181c28",
  border:"#1c2035", borderHi:"#2d3454",
  accent:"#5b7fff", accentSoft:"rgba(91,127,255,0.13)", accentGlow:"rgba(91,127,255,0.28)",
  green:"#3dd68c",  greenSoft:"rgba(61,214,140,0.12)",
  amber:"#f5a623",  amberSoft:"rgba(245,166,35,0.12)",
  red:"#ff6b6b",    redSoft:"rgba(255,107,107,0.12)",
  purple:"#b57bee", purpleSoft:"rgba(181,123,238,0.12)",
  cyan:"#36cfc9",   cyanSoft:"rgba(54,207,201,0.12)",
  pink:"#f06292",   pinkSoft:"rgba(240,98,146,0.12)",
  orange:"#ff9f43", orangeSoft:"rgba(255,159,67,0.11)",
  teal:"#2dd4bf",   tealSoft:"rgba(45,212,191,0.11)",
  text:"#dde1f0", textSub:"#8a92b2", textDim:"#434866",
  mono:"'JetBrains Mono','Fira Code',monospace",
  sans:"'IBM Plex Sans','Inter',system-ui,sans-serif",
};

// ─── Static Data ──────────────────────────────────────────────────
const PROVIDERS = {
  anthropic:{ label:"Anthropic", icon:"◆", color:C.accent, soft:C.accentSoft,
    keyPlaceholder:"sk-ant-api03-…", keyHint:"Anthropic API key",
    models:[
      {id:"claude-opus-4-6",           label:"Claude Opus 4.6",                   reasoning:false},
      {id:"claude-sonnet-4-6",         label:"Claude Sonnet 4.6",                 reasoning:false},
      {id:"claude-haiku-4-5-20251001", label:"Claude Haiku 4.5",                  reasoning:false},
      {id:"claude-sonnet-4-5",         label:"Claude Sonnet 4.5 (Ext. Thinking)", reasoning:true },
    ],
    defaultEndpoint:"https://api.anthropic.com/v1/messages",
  },
  openai:{ label:"OpenAI", icon:"⬡", color:C.green, soft:C.greenSoft,
    keyPlaceholder:"sk-proj-…", keyHint:"OpenAI API key",
    models:[
      {id:"gpt-4o",   label:"GPT-4o",             reasoning:false},
      {id:"gpt-4.1",  label:"GPT-4.1",            reasoning:false},
      {id:"o3",       label:"o3 (Reasoning)",      reasoning:true },
      {id:"o4-mini",  label:"o4-mini (Reasoning)", reasoning:true },
    ],
    defaultEndpoint:"https://api.openai.com/v1/chat/completions",
  },
  google:{ label:"Google", icon:"✦", color:C.amber, soft:C.amberSoft,
    keyPlaceholder:"AIza…", keyHint:"Google AI Studio key",
    models:[
      {id:"gemini-2.5-pro",            label:"Gemini 2.5 Pro",            reasoning:false},
      {id:"gemini-2.5-flash",          label:"Gemini 2.5 Flash",          reasoning:false},
      {id:"gemini-2.0-flash-thinking", label:"Gemini 2.0 Flash Thinking", reasoning:true },
    ],
    defaultEndpoint:"https://generativelanguage.googleapis.com/v1beta/models",
  },
};

const FRAMEWORKS = [
  {id:"auto",           label:"Auto-Select",          icon:"✦", desc:"AI picks the best framework for your model & task"},
  {id:"kernel",         label:"KERNEL",                icon:"⬡", desc:"Keep · Explicit · Narrow · Known · Enforce · Logical"},
  {id:"xml_structured", label:"XML Structured",        icon:"⟨/⟩",desc:"Anthropic XML semantic bounding — best for Claude"},
  {id:"progressive",    label:"Progressive Disclosure",icon:"◈", desc:"Agent Skills layered context injection"},
  {id:"cot_ensemble",   label:"CoT Ensemble",          icon:"⊕", desc:"Medprompt-style multi-path reasoning (Medprompt)"},
  {id:"textgrad",       label:"TextGrad",              icon:"∇", desc:"Iterative textual backpropagation + constraint hardening"},
  {id:"reasoning_aware",label:"Reasoning-Aware",       icon:"◎", desc:"For o-series / extended-thinking — no forced CoT"},
  {id:"tcrte",          label:"TCRTE",                 icon:"⊞", desc:"Task · Context · Role · Tone · Execution — full coverage"},
  {id:"create",         label:"CREATE",                icon:"⟳", desc:"Context · Role · Instruction · Steps · Execution"},
];

const TASK_TYPES = [
  {id:"planning",   label:"Planning",   icon:"📋"},
  {id:"reasoning",  label:"Reasoning",  icon:"🧠"},
  {id:"coding",     label:"Coding",     icon:"💻"},
  {id:"routing",    label:"Routing",    icon:"🔀"},
  {id:"analysis",   label:"Analysis",   icon:"📊"},
  {id:"extraction", label:"Extraction", icon:"🔍"},
  {id:"creative",   label:"Creative",   icon:"✍️"},
  {id:"qa",         label:"Q&A / RAG",  icon:"💬"},
];

const QUICK_ACTIONS = [
  {icon:"✂",    label:"Make V1 more concise"},
  {icon:"🛡",   label:"Add anti-hallucination guards to V2"},
  {icon:"◎",    label:"Convert V3 to reasoning-aware"},
  {icon:"⊕",    label:"Merge best parts of all 3 variants"},
  {icon:"📎",   label:"Add few-shot examples to V2"},
  {icon:"🔒",   label:"Harden output format constraints"},
  {icon:"⚠",    label:"What are the biggest risks here?"},
  {icon:"⟨/⟩",  label:"Rewrite V1 with XML structural bounding"},
  {icon:"⊞",    label:"Apply full TCRTE coverage to V3"},
  {icon:"CoRe", label:"Apply Context Repetition for multi-hop"},
];

// TCRTE dimension metadata
const TCRTE_DIMS = [
  {id:"task",      label:"Task",      color:C.accent,  icon:"T", desc:"Core objective & action"},
  {id:"context",   label:"Context",   color:C.cyan,    icon:"C", desc:"Background & grounding data"},
  {id:"role",      label:"Role",      color:C.purple,  icon:"R", desc:"Model persona & expertise"},
  {id:"tone",      label:"Tone",      color:C.pink,    icon:"T", desc:"Style & communication register"},
  {id:"execution", label:"Execution", color:C.orange,  icon:"E", desc:"Format, length & constraints"},
];

// ─── Prompt Builders ──────────────────────────────────────────────
function buildGapAnalysisPrompt(raw, vars, taskType, provider, model, isReasoning) {
  return `You are an expert prompt engineer. Perform a rapid TCRTE coverage audit on this raw prompt.

TCRTE Dimensions:
- Task: Is the core objective specific, actionable, measurable?
- Context: Is background information, domain knowledge, or data provided?
- Role: Is a model persona/expertise level specified?
- Tone: Are style, register, or audience requirements stated?
- Execution: Are output format, length, constraints, and prohibitions defined?

Target model: ${PROVIDERS[provider]?.label} ${model.label} (${isReasoning?"REASONING":"STANDARD"})
Task type: ${taskType}
${vars?.trim() ? `Input variables declared: ${vars}` : "No input variables declared."}

Raw prompt to audit:
"""
${raw}
"""

Generate a coverage analysis. For each weak/missing dimension, create ONE targeted clarifying question that will unlock the most value. Keep questions concise and practical.

Respond ONLY as valid JSON — no markdown fences:
{
  "tcrte": {
    "task":      {"score":0,"status":"good|weak|missing","note":"short note"},
    "context":   {"score":0,"status":"good|weak|missing","note":"short note"},
    "role":      {"score":0,"status":"good|weak|missing","note":"short note"},
    "tone":      {"score":0,"status":"good|weak|missing","note":"short note"},
    "execution": {"score":0,"status":"good|weak|missing","note":"short note"}
  },
  "overall_score": 0,
  "complexity": "simple|medium|complex",
  "complexity_reason": "one sentence why",
  "recommended_techniques": ["list of: CoRe|RAL-Writer|Prefill|CoT-Ensemble|XML-Bounding|Progressive-Disclosure"],
  "questions": [
    {
      "id": "q1",
      "dimension": "task|context|role|tone|execution",
      "question": "Specific question text",
      "placeholder": "example answer hint",
      "importance": "critical|recommended|optional"
    }
  ],
  "auto_enrichments": ["list of automatic techniques that will be applied"]
}`;
}

function buildOptimizerPrompt(raw, vars, fw, task, provider, model, isReasoning, answers, gapData) {
  const pName = PROVIDERS[provider]?.label || provider;
  const fwInfo = FRAMEWORKS.find(f => f.id === fw) || FRAMEWORKS[0];
  const ttInfo = TASK_TYPES.find(t => t.id === task) || TASK_TYPES[0];
  const complexity = gapData?.complexity || "medium";
  const techniques = gapData?.recommended_techniques || [];
  const useCoRe = techniques.includes("CoRe") || complexity === "complex";
  const useRAL = techniques.includes("RAL-Writer");
  const usePrefill = provider === "anthropic" && techniques.includes("Prefill");

  const answersBlock = answers && Object.keys(answers).length > 0
    ? `\n<gap_interview_answers>\n${Object.entries(answers).map(([q,a])=>`Q: ${q}\nA: ${a}`).join("\n\n")}\n</gap_interview_answers>`
    : "";

  const modelGuide = {
    anthropic:`- Heavy XML semantic tags: <system_directive> <task> <constraints> <context> <input_variables> <output_format>
- Critical constraints FIRST (primacy), echo key rules at END (recency) — "lost in the middle" prevention
- Role → Task → Context → Constraints → Format → Variables
- Nested XML for docs: <documents><document index="1">…</document></documents>
${usePrefill ? "- INCLUDE a <prefill_suggestion> field: the first few tokens of the assistant turn to lock output format" : ""}`,
    openai: isReasoning
      ? `- NO chain-of-thought forcing — reasoning models have native CoT
- Extremely concise system prompt with Markdown structure
- Focus: output format, hard constraints, what NOT to do`
      : `- Markdown: ### headers, **bold**, bullets
- System = role + rules. User = task + injected data
- Triple-backtick fences for code/structured data`,
    google:`- XML angle-bracket tags — Gemini adheres strongly
- Role → Instructions → Examples → Task → Format`,
  };

  const coreBlock = useCoRe
    ? `APPLY CONTEXT REPETITION (CoRe): For multi-hop reasoning, repeat the most critical context segment at the start AND end of the user prompt. Mark repetitions clearly.`
    : "";
  const ralBlock = useRAL
    ? `APPLY RAL-WRITER RESTATE: Identify instructions likely to be "lost in the middle" and restate them at the END of the system prompt inside a <restate_critical> block.`
    : "";

  const fwGuide = {
    kernel:`K-Keep simple (one objective). E-Explicit (MUST NOT as clear as MUST). R-Narrow (one job). N-Known criteria. L-Logical order (Context→Task→Constraints→Format).`,
    xml_structured:`Wrap every semantic zone in XML tags. Isolate user vars. Place <constraints> at TOP. Nest docs.`,
    progressive:`3 layers: DISCOVERY (metadata ~100t) → ACTIVATION (logic, rules, format) → EXECUTION (examples, scripts).`,
    cot_ensemble:`2-3 few-shot examples with reasoning traces. Multi-path instruction. Self-check step. Ensemble synthesis.`,
    textgrad:`Enumerate failure modes. Counter-constraint per mode. Anti-hallucination guard. Completion guard. Rigid output schema.`,
    reasoning_aware:`Simplify prose. No "think step by step". Declare constraints + format UPFRONT. Let model reason autonomously.`,
    tcrte:`Ensure all 5 TCRTE pillars are explicitly addressed: Task clarity, Context grounding, Role definition, Tone specification, Execution constraints. Score each in the output.`,
    create:`Sequential structure: Context → Role → Instruction → Steps → Execution. Force reasoning trace before commitment.`,
    auto:`Auto-select: reasoning models→Reasoning-Aware; multi-doc→XML; agents→Progressive; high-stakes→CoT-Ensemble; coverage gaps→TCRTE.`,
  };

  return `You are an expert AI prompt engineer specialising in context engineering, attention management, and instruction coverage. Transform the raw prompt into 3 production-grade variants.

<target_configuration>
  <provider>${pName}</provider><model>${model.label}</model>
  <model_type>${isReasoning?"REASONING — native CoT, no step-by-step instructions":"STANDARD"}</model_type>
  <task_type>${ttInfo.label}</task_type><complexity>${complexity}</complexity>
  <framework>${fwInfo.label}: ${fwInfo.desc}</framework>
</target_configuration>

<model_guidelines>${modelGuide[provider]||modelGuide.anthropic}</model_guidelines>
<framework_guidelines>${fwGuide[fw]||fwGuide.auto}</framework_guidelines>
${coreBlock ? `<core_technique>${coreBlock}</core_technique>` : ""}
${ralBlock ? `<ral_technique>${ralBlock}</ral_technique>` : ""}

<failure_modes>
  <overshoot>Hallucination, scope creep, infinite loops, applying irrelevant policies</overshoot>
  <undershoot>Ignoring constraints, incomplete output, losing instructions mid-context</undershoot>
</failure_modes>

<raw_prompt>${raw}</raw_prompt>
${vars?.trim()?`<input_variables>${vars}</input_variables>`:""}
${answersBlock}

Generate 3 variants: Conservative (clarity-first), Structured (full framework), Advanced (max guards + all auto-enrichments applied).
${usePrefill?"For the Advanced variant, include a prefill_suggestion field with the ideal first tokens of the assistant turn.":""}

Respond ONLY as valid JSON — no markdown fences:
{
  "analysis":{"detected_issues":[],"model_notes":"","framework_applied":"","coverage_delta":"Coverage improved from X% → Y% after gap answers"},
  "techniques_applied":["CoRe"|"RAL-Writer"|"Prefill"|"XML-Bounding"|etc],
  "variants":[
    {"id":1,"name":"Conservative","strategy":"",
     "system_prompt":"","user_prompt":"",${usePrefill?`"prefill_suggestion":"",`:""}
     "token_estimate":0,"tcrte_scores":{"task":0,"context":0,"role":0,"tone":0,"execution":0},
     "strengths":[],"best_for":"","overshoot_guards":[],"undershoot_guards":[]},
    {"id":2,"name":"Structured",  "strategy":"","system_prompt":"","user_prompt":"","token_estimate":0,"tcrte_scores":{"task":0,"context":0,"role":0,"tone":0,"execution":0},"strengths":[],"best_for":"","overshoot_guards":[],"undershoot_guards":[]},
    {"id":3,"name":"Advanced",    "strategy":"","system_prompt":"","user_prompt":"","token_estimate":0,"tcrte_scores":{"task":0,"context":0,"role":0,"tone":0,"execution":0},"strengths":[],"best_for":"","overshoot_guards":[],"undershoot_guards":[]}
  ]
}`;
}

function buildChatSystem(ctx) {
  if (!ctx) return `You are APOST Assistant — an expert AI prompt engineer. Help users design, refine, and optimise prompts. Topics: TCRTE, KERNEL, XML bounding, CoRe, RAL-Writer, TextGrad, DSPy, Medprompt, overshoot/undershoot, reasoning-model prompting. Be concise, technical, actionable.`;
  const {raw,vars,fw,task,provider,model,isReasoning,result,gapData,answers}=ctx;
  return `You are APOST Assistant — expert prompt engineer in the APOST studio. You help users refine generated prompts conversationally. You have full memory of every message in this thread.

<session_context>
  <raw_prompt>${raw}</raw_prompt>${vars?`\n  <variables>${vars}</variables>`:""}
  <provider>${PROVIDERS[provider]?.label}</provider><model>${model?.label}</model>
  <model_type>${isReasoning?"REASONING":"STANDARD"}</model_type>
  <task>${task}</task><framework>${fw}</framework>
  <complexity>${gapData?.complexity||"unknown"}</complexity>
  <techniques_applied>${result?.techniques_applied?.join(", ")||"none"}</techniques_applied>
</session_context>

${gapData?`<gap_analysis>
  TCRTE overall: ${gapData.overall_score}/100
  ${TCRTE_DIMS.map(d=>`${d.label}: ${gapData.tcrte?.[d.id]?.score||0}/100 (${gapData.tcrte?.[d.id]?.status})`).join(" | ")}
</gap_analysis>`:""}

${answers&&Object.keys(answers).length?`<gap_answers>${Object.entries(answers).map(([q,a])=>`Q:${q} → A:${a}`).join("\n")}</gap_answers>`:""}

<generated_variants>
${(result?.variants||[]).map(v=>`
=== VARIANT ${v.id}: ${v.name} ===
SYSTEM: ${v.system_prompt}
USER: ${v.user_prompt}
${v.prefill_suggestion?`PREFILL: ${v.prefill_suggestion}`:""}
TCRTE: T${v.tcrte_scores?.task||0} C${v.tcrte_scores?.context||0} R${v.tcrte_scores?.role||0} Tone${v.tcrte_scores?.tone||0} E${v.tcrte_scores?.execution||0}
Strengths: ${v.strengths?.join("; ")} | Best for: ${v.best_for}`).join("\n")}
</generated_variants>

Rules: output revised prompts in \`\`\`SYSTEM\n…\`\`\` and \`\`\`USER\n…\`\`\` blocks. Reference prior turns. Explain WHY changes improve coverage or reduce over/undershoot. Be proactive.`;
}

// ─── Small components ─────────────────────────────────────────────
function Spinner({size=16,color="#fff"}){
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.5" style={{flexShrink:0}}>
    <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83">
      <animateTransform attributeName="transform" type="rotate" from="0 12 12" to="360 12 12" dur="0.85s" repeatCount="indefinite"/>
    </path>
  </svg>;
}

function CopyBtn({text}){
  const [ok,setOk]=useState(false);
  return <button onClick={()=>{navigator.clipboard.writeText(text);setOk(true);setTimeout(()=>setOk(false),1800);}}
    style={{background:C.panel,border:`1px solid ${C.border}`,borderRadius:5,color:C.textDim,fontSize:10,fontWeight:600,padding:"2px 8px",cursor:"pointer"}}>
    {ok?"✓":"Copy"}</button>;
}

// TCRTE Score Bar
function TCRTEBar({scores}){
  if(!scores) return null;
  return <div style={{display:"flex",gap:6,flexWrap:"wrap",marginTop:8}}>
    {TCRTE_DIMS.map(d=>{
      const s=scores[d.id]||0;
      const clr = s>=70?C.green : s>=40?C.amber : C.red;
      return <div key={d.id} style={{display:"flex",flexDirection:"column",alignItems:"center",gap:3,minWidth:44}}>
        <div style={{width:44,height:4,background:C.border,borderRadius:2,overflow:"hidden"}}>
          <div style={{width:`${s}%`,height:"100%",background:clr,borderRadius:2,transition:"width 0.5s"}}/>
        </div>
        <span style={{fontSize:9.5,color:clr,fontWeight:700}}>{d.icon}{s}</span>
      </div>;
    })}
  </div>;
}

// Coverage Meter (big visual for gap interview)
function CoverageMeter({tcrte, overall}){
  const clr = overall>=70?C.green : overall>=40?C.amber : C.red;
  return <div style={{background:C.panel,border:`1px solid ${C.border}`,borderRadius:10,padding:"14px 16px"}}>
    <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:14}}>
      <div>
        <div style={{fontSize:10,fontWeight:700,color:C.textDim,letterSpacing:"0.8px",textTransform:"uppercase",marginBottom:3}}>TCRTE Coverage</div>
        <div style={{fontSize:11,color:C.textSub}}>Prompt completeness audit</div>
      </div>
      <div style={{textAlign:"center"}}>
        <div style={{fontSize:30,fontWeight:800,color:clr,lineHeight:1}}>{overall}</div>
        <div style={{fontSize:10,color:C.textDim,fontWeight:600}}>/100</div>
      </div>
    </div>
    {TCRTE_DIMS.map(d=>{
      const dim=tcrte?.[d.id]||{score:0,status:"missing",note:""};
      const s=dim.score||0;
      const statusClr = dim.status==="good"?C.green : dim.status==="weak"?C.amber : C.red;
      const statusBg  = dim.status==="good"?C.greenSoft : dim.status==="weak"?C.amberSoft : C.redSoft;
      return <div key={d.id} style={{marginBottom:9}}>
        <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:3}}>
          <div style={{display:"flex",alignItems:"center",gap:7}}>
            <span style={{background:statusBg,color:statusClr,border:`1px solid ${statusClr}30`,borderRadius:4,padding:"1px 7px",fontSize:10,fontWeight:700}}>{dim.status.toUpperCase()}</span>
            <span style={{fontSize:12,fontWeight:600,color:C.text}}>{d.label}</span>
            <span style={{fontSize:10.5,color:C.textDim}}>{d.desc}</span>
          </div>
          <span style={{fontSize:11,fontWeight:700,color:statusClr,fontFamily:C.mono}}>{s}%</span>
        </div>
        <div style={{height:5,background:C.border,borderRadius:3,overflow:"hidden"}}>
          <div style={{width:`${s}%`,height:"100%",background:`linear-gradient(90deg,${statusClr}99,${statusClr})`,borderRadius:3,transition:"width 0.6s"}}/>
        </div>
        {dim.note&&<div style={{fontSize:10.5,color:C.textDim,marginTop:2,paddingLeft:2}}>{dim.note}</div>}
      </div>;
    })}
  </div>;
}

// ─── Variant Output Card ──────────────────────────────────────────
function VariantCard({variant,index,onRefine}){
  const [tab,setTab]=useState("system");
  const cols=[C.accent,C.green,C.purple];
  const softs=[C.accentSoft,C.greenSoft,C.purpleSoft];
  const col=cols[index];

  return <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:11,overflow:"hidden",marginBottom:14}}>
    <div style={{background:`linear-gradient(90deg,${col}12 0%,transparent 100%)`,borderBottom:`1px solid ${C.border}`,padding:"10px 14px",display:"flex",alignItems:"center",justifyContent:"space-between"}}>
      <div style={{display:"flex",alignItems:"center",gap:7}}>
        <span style={{background:softs[index],color:col,border:`1px solid ${col}35`,borderRadius:20,padding:"2px 9px",fontSize:10.5,fontWeight:700}}>V{variant.id}</span>
        <span style={{fontSize:13,fontWeight:700,color:C.text}}>{variant.name}</span>
        <span style={{fontSize:10.5,color:C.textDim,fontFamily:C.mono}}>~{variant.token_estimate}t</span>
      </div>
      <button onClick={()=>onRefine(variant)} style={{background:C.pinkSoft,border:`1px solid ${C.pink}35`,borderRadius:6,color:C.pink,fontSize:10.5,fontWeight:700,padding:"4px 10px",cursor:"pointer"}}>✦ Refine</button>
    </div>
    <div style={{padding:"10px 14px 0"}}>
      <div style={{fontSize:11.5,color:C.textSub,fontStyle:"italic",marginBottom:10}}>{variant.strategy}</div>
      {/* TCRTE mini bars */}
      <TCRTEBar scores={variant.tcrte_scores}/>
      {/* Tabs */}
      <div style={{display:"flex",gap:2,background:C.bg,padding:"3px",borderRadius:7,margin:"10px 0 8px"}}>
        {[["system","System"],["user","User"],["guards","Guards"],["meta","Meta"],["prefill","Prefill"]].filter(([id])=>id!=="prefill"||variant.prefill_suggestion).map(([id,lbl])=>(
          <button key={id} onClick={()=>setTab(id)} style={{flex:1,padding:"5px",borderRadius:5,fontSize:10.5,fontWeight:600,cursor:"pointer",background:tab===id?C.surface:"transparent",color:tab===id?C.text:C.textDim,border:"none",transition:"all 0.12s"}}>{lbl}</button>
        ))}
      </div>
      {tab==="system"&&<div style={{paddingBottom:14}}><div style={{display:"flex",justifyContent:"flex-end",marginBottom:4}}><CopyBtn text={variant.system_prompt}/></div><pre style={{background:C.bg,border:`1px solid ${C.border}`,borderRadius:7,padding:"10px 12px",fontFamily:C.mono,fontSize:11,color:C.cyan,lineHeight:1.65,whiteSpace:"pre-wrap",wordBreak:"break-word",margin:0,overflowX:"auto",userSelect:"text"}}>{variant.system_prompt}</pre></div>}
      {tab==="user"&&<div style={{paddingBottom:14}}><div style={{display:"flex",justifyContent:"flex-end",marginBottom:4}}><CopyBtn text={variant.user_prompt}/></div><pre style={{background:C.bg,border:`1px solid ${C.border}`,borderRadius:7,padding:"10px 12px",fontFamily:C.mono,fontSize:11,color:C.amber,lineHeight:1.65,whiteSpace:"pre-wrap",wordBreak:"break-word",margin:0,overflowX:"auto",userSelect:"text"}}>{variant.user_prompt}</pre></div>}
      {tab==="guards"&&<div style={{paddingBottom:14,display:"flex",flexDirection:"column",gap:12}}>
        <div><div style={{fontSize:9.5,fontWeight:700,color:C.red,letterSpacing:"0.8px",textTransform:"uppercase",marginBottom:6}}>⟲ Anti-Overshoot</div>{(variant.overshoot_guards||[]).map((g,i)=><div key={i} style={{display:"flex",gap:6,fontSize:11.5,color:C.textSub,marginBottom:4,lineHeight:1.5}}><span style={{color:C.red,flexShrink:0}}>▸</span>{g}</div>)}</div>
        <div><div style={{fontSize:9.5,fontWeight:700,color:C.green,letterSpacing:"0.8px",textTransform:"uppercase",marginBottom:6}}>⟳ Anti-Undershoot</div>{(variant.undershoot_guards||[]).map((g,i)=><div key={i} style={{display:"flex",gap:6,fontSize:11.5,color:C.textSub,marginBottom:4,lineHeight:1.5}}><span style={{color:C.green,flexShrink:0}}>▸</span>{g}</div>)}</div>
      </div>}
      {tab==="meta"&&<div style={{paddingBottom:14,display:"flex",flexDirection:"column",gap:10}}>
        <div><div style={{fontSize:9.5,fontWeight:700,color:C.accent,letterSpacing:"0.8px",textTransform:"uppercase",marginBottom:6}}>Strengths</div>{(variant.strengths||[]).map((s,i)=><div key={i} style={{display:"flex",gap:6,fontSize:11.5,color:C.textSub,marginBottom:4,lineHeight:1.5}}><span style={{color:C.accent}}>✦</span>{s}</div>)}</div>
        <div style={{background:C.bg,borderRadius:7,padding:"8px 11px"}}><span style={{fontSize:9.5,fontWeight:700,color:C.purple,textTransform:"uppercase",letterSpacing:"0.5px"}}>Best For: </span><span style={{fontSize:11.5,color:C.textSub}}>{variant.best_for}</span></div>
      </div>}
      {tab==="prefill"&&variant.prefill_suggestion&&<div style={{paddingBottom:14}}>
        <div style={{fontSize:9.5,fontWeight:700,color:C.teal,letterSpacing:"0.8px",textTransform:"uppercase",marginBottom:8}}>Claude Prefill — paste as start of assistant turn</div>
        <div style={{background:C.bg,border:`1px solid ${C.teal}40`,borderRadius:7,padding:"10px 12px",position:"relative"}}>
          <pre style={{fontFamily:C.mono,fontSize:11,color:C.teal,margin:0,whiteSpace:"pre-wrap",wordBreak:"break-word"}}>{variant.prefill_suggestion}</pre>
          <div style={{position:"absolute",top:7,right:7}}><CopyBtn text={variant.prefill_suggestion}/></div>
        </div>
        <div style={{fontSize:10.5,color:C.textDim,marginTop:6}}>Prefilling locks the assistant's output format by providing the first tokens. Bypasses conversational preamble.</div>
      </div>}
    </div>
  </div>;
}

// ─── Chat Bubble ──────────────────────────────────────────────────
function ChatBubble({msg}){
  const isUser=msg.role==="user";
  const renderAI=(text)=>{
    const parts=text.split(/(```[\s\S]*?```)/g);
    return parts.map((part,i)=>{
      if(part.startsWith("```")){
        const lines=part.split("\n");
        const lang=lines[0].replace("```","").trim();
        const body=lines.slice(1).join("\n").replace(/```$/,"");
        return <div key={i} style={{margin:"8px 0",position:"relative"}}>
          {lang&&<div style={{fontSize:9.5,fontWeight:700,color:C.textDim,textTransform:"uppercase",letterSpacing:"0.5px",marginBottom:3}}>{lang}</div>}
          <pre style={{background:C.bg,border:`1px solid ${C.border}`,borderRadius:7,padding:"9px 11px",fontFamily:C.mono,fontSize:10.5,color:C.cyan,whiteSpace:"pre-wrap",wordBreak:"break-word",margin:0,overflowX:"auto"}}>{body}</pre>
          <div style={{position:"absolute",top:lang?26:6,right:6}}><CopyBtn text={body}/></div>
        </div>;
      }
      const b=part.split(/(\*\*[^*]+\*\*)/g).map((bp,j)=>bp.startsWith("**")?<strong key={j} style={{color:C.text,fontWeight:700}}>{bp.replace(/\*\*/g,"")}</strong>:<span key={j} style={{whiteSpace:"pre-wrap"}}>{bp}</span>);
      return <span key={i}>{b}</span>;
    });
  };
  return <div style={{display:"flex",flexDirection:"column",alignItems:isUser?"flex-end":"flex-start",gap:3}}>
    <div style={{fontSize:9.5,color:C.textDim,fontWeight:700,letterSpacing:"0.6px",paddingLeft:isUser?0:2,paddingRight:isUser?2:0}}>{isUser?"YOU":"✦ APOST AI"}</div>
    <div style={isUser?{maxWidth:"88%",background:`linear-gradient(135deg,${C.accent}1e,${C.purple}1e)`,border:`1px solid ${C.accent}30`,borderRadius:"11px 11px 3px 11px",padding:"9px 12px",fontSize:12.5,color:C.text,lineHeight:1.55}:{maxWidth:"96%",background:C.panel,border:`1px solid ${C.border}`,borderRadius:"11px 11px 11px 3px",padding:"9px 12px",fontSize:12,color:C.text,lineHeight:1.68,wordBreak:"break-word"}}>
      {isUser?<span style={{whiteSpace:"pre-wrap"}}>{msg.content}</span>:renderAI(msg.content)}
    </div>
    {msg.ts&&<div style={{fontSize:9.5,color:C.textDim}}>{msg.ts}</div>}
  </div>;
}

// ─── Main App ─────────────────────────────────────────────────────
export default function App(){
  // Left panel
  const [rawPrompt,setRawPrompt]=useState("");
  const [variables,setVariables]=useState("");
  const [provider,setProvider]=useState("anthropic");
  const [modelId,setModelId]=useState("claude-sonnet-4-6");
  const [apiKey,setApiKey]=useState("");
  const [showKey,setShowKey]=useState(false);
  const [endpoint,setEndpoint]=useState("");

  // Middle panel state machine
  // "idle" | "analyzing" | "interview" | "optimizing" | "results"
  const [phase,setPhase]=useState("idle");
  const [taskType,setTaskType]=useState("reasoning");
  const [framework,setFramework]=useState("auto");
  const [gapData,setGapData]=useState(null);
  const [answers,setAnswers]=useState({});
  const [result,setResult]=useState(null);
  const [error,setError]=useState("");

  // Chat
  const [chatOpen,setChatOpen]=useState(true);
  const [msgs,setMsgs]=useState([]);
  const [chatInput,setChatInput]=useState("");
  const [chatLoading,setChatLoading]=useState(false);
  const histRef=useRef([]);
  const ctxRef=useRef(null);
  const endRef=useRef(null);
  const inputRef=useRef(null);

  const pData=PROVIDERS[provider];
  const models=pData.models;
  const selModel=models.find(m=>m.id===modelId)||models[0];
  const isReasoning=selModel.reasoning;
  const exchangeCount=msgs.filter(m=>m.role==="user").length;

  useEffect(()=>{endRef.current?.scrollIntoView({behavior:"smooth"});},[msgs,chatLoading]);

  const changeProvider=(p)=>{setProvider(p);setModelId(PROVIDERS[p].models[0].id);setEndpoint("");setApiKey("");};
  const reset=()=>{setPhase("idle");setGapData(null);setAnswers({});setResult(null);setError("");histRef.current=[];setMsgs([]);ctxRef.current=null;};

  // ── Step 1: Gap Analysis ────────────────────────────────────────
  const analyseGaps=useCallback(async()=>{
    if(!rawPrompt.trim()){setError("Enter a raw prompt first.");return;}
    if(!apiKey.trim()){setError(`Enter your ${pData.label} API key.`);return;}
    setError("");setPhase("analyzing");setGapData(null);setAnswers({});

    try{
      const p=buildGapAnalysisPrompt(rawPrompt,variables,taskType,provider,selModel,isReasoning);
      const res=await fetch("https://api.anthropic.com/v1/messages",{
        method:"POST",
        headers:{"Content-Type":"application/json","x-api-key":apiKey,"anthropic-version":"2023-06-01"},
        body:JSON.stringify({model:"claude-sonnet-4-20250514",max_tokens:1200,messages:[{role:"user",content:p}]}),
      });
      if(!res.ok){const e=await res.json();throw new Error(e?.error?.message||`API ${res.status}`);}
      const data=await res.json();
      const text=data.content.map(b=>b.text||"").join("");
      const clean=text.replace(/```json\s*/g,"").replace(/```\s*/g,"").trim();
      const parsed=JSON.parse(clean);
      setGapData(parsed);
      setPhase("interview");
    }catch(e){
      setError(`Gap analysis error: ${e.message}`);
      setPhase("idle");
    }
  },[rawPrompt,variables,taskType,provider,selModel,isReasoning,apiKey,pData]);

  // ── Step 2: Optimise ────────────────────────────────────────────
  const optimise=useCallback(async(skipInterview=false)=>{
    if(!rawPrompt.trim()){setError("Enter a raw prompt first.");return;}
    if(!apiKey.trim()){setError(`Enter your ${pData.label} API key.`);return;}
    setError("");setPhase("optimizing");setResult(null);
    histRef.current=[];setMsgs([]);ctxRef.current=null;

    const usedAnswers=skipInterview?{}:answers;
    const usedGap=skipInterview?null:gapData;

    try{
      const p=buildOptimizerPrompt(rawPrompt,variables,framework,taskType,provider,selModel,isReasoning,usedAnswers,usedGap);
      const res=await fetch("https://api.anthropic.com/v1/messages",{
        method:"POST",
        headers:{"Content-Type":"application/json","x-api-key":apiKey,"anthropic-version":"2023-06-01"},
        body:JSON.stringify({model:"claude-sonnet-4-20250514",max_tokens:4096,messages:[{role:"user",content:p}]}),
      });
      if(!res.ok){const e=await res.json();throw new Error(e?.error?.message||`API ${res.status}`);}
      const data=await res.json();
      const text=data.content.map(b=>b.text||"").join("");
      const clean=text.replace(/```json\s*/g,"").replace(/```\s*/g,"").trim();
      const parsed=JSON.parse(clean);
      setResult(parsed);
      setPhase("results");

      const ctx={raw:rawPrompt,vars:variables,fw:framework,task:taskType,provider,model:selModel,isReasoning,result:parsed,gapData:usedGap,answers:usedAnswers};
      ctxRef.current=ctx;

      // Seed chat with full output
      const ts=new Date().toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"});
      const delta=parsed.analysis?.coverage_delta||"";
      const techApplied=(parsed.techniques_applied||[]).join(", ")||"standard optimisation";
      const seed={role:"assistant",content:`✦ Optimisation complete.\n\n**${parsed.analysis?.framework_applied}**\n${delta?`**${delta}**\n`:""}\n**Techniques applied:** ${techApplied}\n\n**Issues fixed:** ${parsed.analysis?.detected_issues?.slice(0,3).join("; ")}\n\n---\n\n${(parsed.variants||[]).map(v=>`**Variant ${v.id} — ${v.name}** (~${v.token_estimate}t)\n${v.strategy}\n\nTCRTE: T${v.tcrte_scores?.task||0} C${v.tcrte_scores?.context||0} R${v.tcrte_scores?.role||0} Tone${v.tcrte_scores?.tone||0} E${v.tcrte_scores?.execution||0}\n\n\`\`\`SYSTEM\n${v.system_prompt}\n\`\`\`\n\`\`\`USER\n${v.user_prompt}\n\`\`\`${v.prefill_suggestion?`\n\`\`\`PREFILL\n${v.prefill_suggestion}\n\`\`\``:""}`)}\n\n---\nI have full context of all 3 variants + your gap answers. What would you like to refine?`,ts};
      histRef.current=[seed];
      setMsgs([seed]);
      setChatOpen(true);
    }catch(e){
      setError(`Optimisation error: ${e.message}`);
      setPhase(gapData?"interview":"idle");
    }
  },[rawPrompt,variables,framework,taskType,provider,selModel,isReasoning,apiKey,pData,answers,gapData]);

  // ── Chat send ───────────────────────────────────────────────────
  const sendChat=useCallback(async(override)=>{
    const text=(override??chatInput).trim();
    if(!text||chatLoading)return;
    if(!apiKey.trim()){setError(`Enter your ${pData.label} API key.`);return;}
    const ts=new Date().toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"});
    setChatInput("");
    const userMsg={role:"user",content:text,ts};
    const hist=[...histRef.current,userMsg];
    histRef.current=hist;setMsgs([...hist]);setChatLoading(true);
    try{
      const sys=buildChatSystem(ctxRef.current);
      const apiMsgs=hist.slice(-28).map(({role,content})=>({role,content}));
      const res=await fetch("https://api.anthropic.com/v1/messages",{
        method:"POST",
        headers:{"Content-Type":"application/json","x-api-key":apiKey,"anthropic-version":"2023-06-01"},
        body:JSON.stringify({model:"claude-sonnet-4-20250514",max_tokens:2048,system:sys,messages:apiMsgs}),
      });
      if(!res.ok){const e=await res.json();throw new Error(e?.error?.message||`API ${res.status}`);}
      const data=await res.json();
      const reply=data.content.map(b=>b.text||"").join("");
      const aMsg={role:"assistant",content:reply,ts:new Date().toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"})};
      const final=[...hist,aMsg];histRef.current=final;setMsgs([...final]);
    }catch(e){
      const err={role:"assistant",content:`⚠ ${e.message}`,ts:new Date().toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"})};
      const final=[...hist,err];histRef.current=final;setMsgs([...final]);
    }finally{setChatLoading(false);}
  },[chatInput,chatLoading,apiKey,pData]);

  const handleRefine=(v)=>{
    const msg=`Refine Variant ${v.id} "${v.name}" (strategy: "${v.strategy}"). Show the most impactful improvements with full revised SYSTEM + USER prompts.`;
    setChatOpen(true);setTimeout(()=>{setChatInput(msg);inputRef.current?.focus();},80);
  };

  // ── Shared micro-styles ─────────────────────────────────────────
  const inp={width:"100%",background:C.panel,border:`1px solid ${C.border}`,borderRadius:8,color:C.text,fontFamily:C.mono,fontSize:12,padding:"9px 11px",outline:"none",boxSizing:"border-box",transition:"border-color 0.15s"};
  const secTitle={fontSize:10,fontWeight:700,color:C.textDim,letterSpacing:"1.1px",textTransform:"uppercase",marginBottom:10,display:"flex",alignItems:"center",gap:6};
  const lbl={fontSize:11,fontWeight:600,color:C.textSub,marginBottom:5,display:"block"};
  const chip=(active,col,soft)=>({padding:"5px 10px",borderRadius:6,fontSize:11.5,fontWeight:600,cursor:"pointer",border:active?`1.5px solid ${col}`:`1px solid ${C.border}`,background:active?soft:"transparent",color:active?col:C.textSub,transition:"all 0.13s"});

  // Complexity colours
  const complexityMeta={simple:{label:"Simple",color:C.green,bg:C.greenSoft},medium:{label:"Medium",color:C.amber,bg:C.amberSoft},complex:{label:"Complex",color:C.red,bg:C.redSoft}};
  const cx=complexityMeta[gapData?.complexity||"medium"];

  // ─────────────────────────────────────────────────────────────────
  return <div style={{fontFamily:C.sans,background:C.bg,minHeight:"100vh",color:C.text,display:"flex",flexDirection:"column"}}>

    {/* ═══ HEADER ═══════════════════════════════════════════════ */}
    <div style={{background:C.surface,borderBottom:`1px solid ${C.border}`,padding:"11px 22px",display:"flex",alignItems:"center",gap:13,flexShrink:0}}>
      <div style={{width:32,height:32,background:`linear-gradient(135deg,${C.accent},${C.purple})`,borderRadius:8,display:"flex",alignItems:"center",justifyContent:"center",fontSize:16,flexShrink:0}}>⬡</div>
      <div>
        <div style={{fontSize:15.5,fontWeight:700,letterSpacing:"-0.3px"}}>APOST — Prompt Optimisation Studio</div>
        <div style={{fontSize:11,color:C.textSub,marginTop:1}}>Smart Gap Analysis · TCRTE Coverage · CoRe · RAL-Writer · Prefill · AI Refinement Chat</div>
      </div>
      <div style={{marginLeft:"auto",display:"flex",gap:6}}>
        {[["v4.0",C.green,C.greenSoft],["TCRTE",C.cyan,C.cyanSoft],["CoRe+RAL",C.orange,C.orangeSoft],["+AI Chat",C.pink,C.pinkSoft]].map(([t,c,s])=>(
          <span key={t} style={{background:s,color:c,border:`1px solid ${c}30`,borderRadius:4,padding:"2px 8px",fontSize:10,fontWeight:700,letterSpacing:"0.5px",textTransform:"uppercase",fontFamily:C.mono}}>{t}</span>
        ))}
      </div>
    </div>

    {/* ═══ THREE-COLUMN BODY ════════════════════════════════════ */}
    <div style={{display:"flex",flex:1,overflow:"hidden",height:"calc(100vh - 55px)"}}>

      {/* ─── LEFT: Prompt + Model ─────────────────────────────── */}
      <div style={{width:340,flexShrink:0,background:C.surface,borderRight:`1px solid ${C.border}`,overflowY:"auto",display:"flex",flexDirection:"column"}}>

        {/* Prompt */}
        <div style={{padding:"16px 17px",borderBottom:`1px solid ${C.border}`}}>
          <div style={secTitle}><span>✍</span> Prompt Input</div>
          <label style={lbl}>Raw Prompt</label>
          <textarea rows={7} placeholder={"e.g. Analyze these financial documents and identify all risk factors…"} value={rawPrompt} onChange={e=>{setRawPrompt(e.target.value);if(phase!=="idle")reset();}}
            style={{...inp,fontFamily:C.mono,resize:"vertical",lineHeight:1.6,fontSize:11.5}}/>
          <div style={{marginTop:11}}>
            <label style={lbl}>Input Variables <span style={{color:C.textDim,fontWeight:400}}>(optional)</span></label>
            <textarea rows={3} placeholder={"{{documents}} – array of PDFs\n{{threshold}} – risk %"} value={variables} onChange={e=>setVariables(e.target.value)}
              style={{...inp,fontFamily:C.mono,fontSize:11,resize:"vertical",lineHeight:1.6}}/>
          </div>
        </div>

        {/* Model */}
        <div style={{padding:"16px 17px",borderBottom:`1px solid ${C.border}`}}>
          <div style={secTitle}><span>🎯</span> Target Model</div>
          <label style={lbl}>Provider</label>
          <div style={{display:"flex",gap:5,flexWrap:"wrap",marginBottom:12}}>
            {Object.entries(PROVIDERS).map(([key,p])=>(
              <button key={key} onClick={()=>changeProvider(key)} style={chip(provider===key,p.color,p.soft)}>{p.icon} {p.label}</button>
            ))}
          </div>
          <label style={lbl}>Model</label>
          <select value={modelId} onChange={e=>setModelId(e.target.value)} style={{...inp,fontFamily:C.sans,cursor:"pointer",marginBottom:12}}>
            {models.map(m=><option key={m.id} value={m.id}>{m.label}</option>)}
          </select>
          {isReasoning&&<div style={{display:"flex",alignItems:"center",gap:7,padding:"7px 10px",background:C.amberSoft,borderRadius:7,border:`1px solid ${C.amber}30`,marginBottom:12}}>
            <span>⚡</span><span style={{fontSize:11.5,color:C.amber,fontWeight:600}}>Reasoning model — CoT auto-suppressed</span>
          </div>}
          <label style={lbl}>{pData.keyHint} <span style={{color:C.red}}>*</span></label>
          <div style={{position:"relative",marginBottom:10}}>
            <input type={showKey?"text":"password"} placeholder={pData.keyPlaceholder} value={apiKey} onChange={e=>setApiKey(e.target.value)} style={{...inp,paddingRight:48,color:apiKey?pData.color:C.textSub}}/>
            <button onClick={()=>setShowKey(s=>!s)} style={{position:"absolute",right:10,top:"50%",transform:"translateY(-50%)",background:"none",border:"none",color:C.textDim,cursor:"pointer",fontSize:10.5}}>{showKey?"hide":"show"}</button>
          </div>
          <label style={lbl}>API Endpoint <span style={{color:C.textDim,fontWeight:400}}>(override)</span></label>
          <input placeholder={pData.defaultEndpoint} value={endpoint} onChange={e=>setEndpoint(e.target.value)} style={{...inp,fontSize:10.5,color:C.textSub}}/>
        </div>

        {/* Info panel — what the tool does */}
        <div style={{padding:"14px 17px",flex:1}}>
          <div style={secTitle}><span>⟳</span> How It Works</div>
          {[["1","🔍 Analyse Gaps","TCRTE coverage audit — finds what's missing in your prompt"],["2","🎯 Answer Questions","Fill gaps with targeted Q&A — no prompt knowledge needed"],["3","⬡ Optimise","3 production variants generated with CoRe, RAL-Writer & guards"],["4","✦ Refine in Chat","AI chat has full context — iterate conversationally"]].map(([n,title,desc])=>(
            <div key={n} style={{display:"flex",gap:10,marginBottom:12}}>
              <div style={{width:20,height:20,background:C.accentSoft,border:`1px solid ${C.accent}30`,borderRadius:"50%",display:"flex",alignItems:"center",justifyContent:"center",fontSize:10.5,fontWeight:700,color:C.accent,flexShrink:0,marginTop:1}}>{n}</div>
              <div><div style={{fontSize:12,fontWeight:700,color:C.text,marginBottom:2}}>{title}</div><div style={{fontSize:11,color:C.textDim,lineHeight:1.5}}>{desc}</div></div>
            </div>
          ))}
        </div>
      </div>

      {/* ─── MIDDLE: Controls + State Machine ─────────────────── */}
      <div style={{flex:1,background:C.bg,display:"flex",flexDirection:"column",overflow:"hidden",minWidth:0}}>

        {/* Controls strip (always visible) */}
        <div style={{background:C.surface,borderBottom:`1px solid ${C.border}`,padding:"14px 18px",flexShrink:0}}>
          {/* Task Type */}
          <div style={{...secTitle,marginBottom:8}}><span>⚙</span> Task Type</div>
          <div style={{display:"flex",flexWrap:"wrap",gap:5,marginBottom:14}}>
            {TASK_TYPES.map(t=><button key={t.id} onClick={()=>setTaskType(t.id)} style={chip(taskType===t.id,C.cyan,C.cyanSoft)}>{t.icon} {t.label}</button>)}
          </div>
          {/* Framework */}
          <div style={{...secTitle,marginBottom:8}}><span>◈</span> Optimisation Framework</div>
          <div style={{display:"flex",flexWrap:"wrap",gap:5,marginBottom:6}}>
            {FRAMEWORKS.map(f=><button key={f.id} onClick={()=>setFramework(f.id)} style={chip(framework===f.id,C.purple,C.purpleSoft)}>{f.icon} {f.label}</button>)}
          </div>
          {framework!=="auto"&&<div style={{fontSize:10.5,color:C.textDim,marginBottom:12,paddingLeft:2}}>↳ {FRAMEWORKS.find(f=>f.id===framework)?.desc}</div>}

          {/* Error */}
          {error&&<div style={{padding:"8px 11px",background:C.redSoft,border:`1px solid ${C.red}30`,borderRadius:7,fontSize:12,color:C.red,marginBottom:10,lineHeight:1.5}}>{error}</div>}

          {/* Action buttons */}
          <div style={{display:"flex",gap:8}}>
            {phase==="idle"&&<>
              <button onClick={analyseGaps} style={{flex:2,background:`linear-gradient(135deg,${C.teal},${C.cyan})`,color:C.bg,border:"none",borderRadius:9,padding:"11px",fontSize:13,fontWeight:700,cursor:"pointer",display:"flex",alignItems:"center",justifyContent:"center",gap:7}}>
                🔍 Analyse Gaps First
              </button>
              <button onClick={()=>optimise(true)} style={{flex:1,background:C.panel,border:`1px solid ${C.border}`,borderRadius:9,padding:"11px",fontSize:12,fontWeight:700,cursor:"pointer",color:C.textSub}}>
                Skip → Optimise
              </button>
            </>}
            {phase==="interview"&&<>
              <button onClick={()=>optimise(false)} style={{flex:2,background:`linear-gradient(135deg,${C.accent},${C.purple})`,color:"#fff",border:"none",borderRadius:9,padding:"11px",fontSize:13,fontWeight:700,cursor:"pointer",display:"flex",alignItems:"center",justifyContent:"center",gap:7}}>
                ⬡ Optimise with Context
              </button>
              <button onClick={()=>optimise(true)} style={{flex:1,background:C.panel,border:`1px solid ${C.border}`,borderRadius:9,padding:"11px",fontSize:12,fontWeight:700,cursor:"pointer",color:C.textSub}}>
                Skip Answers
              </button>
            </>}
            {(phase==="results")&&<>
              <button onClick={reset} style={{flex:1,background:C.panel,border:`1px solid ${C.border}`,borderRadius:9,padding:"11px",fontSize:12,fontWeight:700,cursor:"pointer",color:C.textSub}}>
                ↺ Reset
              </button>
              <button onClick={()=>optimise(false)} style={{flex:2,background:`linear-gradient(135deg,${C.accent},${C.purple})`,color:"#fff",border:"none",borderRadius:9,padding:"11px",fontSize:13,fontWeight:700,cursor:"pointer",display:"flex",alignItems:"center",justifyContent:"center",gap:7}}>
                ⬡ Re-Optimise
              </button>
            </>}
          </div>
        </div>

        {/* Phase-based output area */}
        <div style={{flex:1,overflowY:"auto",padding:"18px"}}>

          {/* ── IDLE ── */}
          {phase==="idle"&&<div style={{display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",height:"100%",gap:14,textAlign:"center",color:C.textSub}}>
            <div style={{fontSize:46,opacity:0.12}}>⬡</div>
            <div style={{fontSize:17,fontWeight:700,color:C.text,marginBottom:4}}>Ready for intelligent optimisation</div>
            <div style={{fontSize:12.5,color:C.textSub,maxWidth:380,lineHeight:1.7}}>
              Click <strong style={{color:C.teal}}>🔍 Analyse Gaps First</strong> — the tool will audit your prompt against the TCRTE framework, score each dimension, and ask you targeted questions to fill the gaps before optimising.<br/><br/>
              Or click <strong style={{color:C.textSub}}>Skip → Optimise</strong> to run directly.
            </div>
            <div style={{display:"flex",flexWrap:"wrap",gap:6,justifyContent:"center",marginTop:4}}>
              {["TCRTE Gap Scoring","CoRe Multi-hop","RAL-Writer Restate","Claude Prefill","TextGrad Guards","3 Variants"].map(t=>(
                <span key={t} style={{background:C.surface,color:C.textDim,border:`1px solid ${C.border}`,borderRadius:4,padding:"3px 8px",fontSize:10,fontWeight:600}}>{t}</span>
              ))}
            </div>
          </div>}

          {/* ── ANALYZING ── */}
          {phase==="analyzing"&&<div style={{display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",height:"100%",gap:14}}>
            <Spinner size={36} color={C.teal}/>
            <div style={{fontSize:14,fontWeight:600,color:C.text}}>Running TCRTE gap analysis…</div>
            <div style={{fontSize:12,color:C.textSub}}>Auditing Task · Context · Role · Tone · Execution coverage</div>
          </div>}

          {/* ── INTERVIEW ── */}
          {phase==="interview"&&gapData&&<div>
            {/* Coverage meter */}
            <CoverageMeter tcrte={gapData.tcrte} overall={gapData.overall_score||0}/>

            {/* Complexity + recommended techniques */}
            <div style={{display:"flex",gap:8,marginTop:12,marginBottom:16,flexWrap:"wrap"}}>
              <div style={{background:cx.bg,border:`1px solid ${cx.color}30`,borderRadius:7,padding:"7px 12px",display:"flex",alignItems:"center",gap:7}}>
                <span style={{fontSize:11,fontWeight:700,color:cx.color,textTransform:"uppercase",letterSpacing:"0.5px"}}>Complexity: {cx.label}</span>
                <span style={{fontSize:10.5,color:C.textDim}}>{gapData.complexity_reason}</span>
              </div>
              {(gapData.recommended_techniques||[]).map(t=>(
                <span key={t} style={{background:C.panel,border:`1px solid ${C.borderHi}`,borderRadius:6,padding:"5px 10px",fontSize:10.5,color:C.cyan,fontWeight:600}}>{t}</span>
              ))}
            </div>

            {/* Auto-enrichments */}
            {(gapData.auto_enrichments||[]).length>0&&<div style={{background:C.tealSoft,border:`1px solid ${C.teal}30`,borderRadius:8,padding:"10px 13px",marginBottom:16}}>
              <div style={{fontSize:9.5,fontWeight:700,color:C.teal,letterSpacing:"0.8px",textTransform:"uppercase",marginBottom:6}}>Auto-Enrichments Applied</div>
              {gapData.auto_enrichments.map((e,i)=><div key={i} style={{display:"flex",gap:6,fontSize:11.5,color:C.teal,marginBottom:3}}><span>⟳</span>{e}</div>)}
            </div>}

            {/* Questions */}
            {(gapData.questions||[]).length>0&&<div>
              <div style={{fontSize:10,fontWeight:700,color:C.textDim,letterSpacing:"0.8px",textTransform:"uppercase",marginBottom:12}}>
                Gap-Filling Questions ({gapData.questions.length}) — answer to improve coverage
              </div>
              {gapData.questions.map((q,i)=>{
                const dim=TCRTE_DIMS.find(d=>d.id===q.dimension)||TCRTE_DIMS[0];
                const importanceColor=q.importance==="critical"?C.red:q.importance==="recommended"?C.amber:C.textDim;
                const importanceBg=q.importance==="critical"?C.redSoft:q.importance==="recommended"?C.amberSoft:C.panel;
                return <div key={q.id} style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:10,padding:"13px 14px",marginBottom:10}}>
                  <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:9}}>
                    <span style={{background:dim.color+"20",color:dim.color,border:`1px solid ${dim.color}30`,borderRadius:5,padding:"2px 8px",fontSize:10,fontWeight:700,letterSpacing:"0.5px"}}>{dim.label.toUpperCase()}</span>
                    <span style={{background:importanceBg,color:importanceColor,border:`1px solid ${importanceColor}30`,borderRadius:5,padding:"2px 8px",fontSize:10,fontWeight:700,letterSpacing:"0.4px",textTransform:"uppercase"}}>{q.importance}</span>
                    <span style={{fontSize:11.5,fontWeight:600,color:C.text,flex:1}}>{q.question}</span>
                  </div>
                  <input
                    placeholder={q.placeholder}
                    value={answers[q.question]||""}
                    onChange={e=>setAnswers(prev=>({...prev,[q.question]:e.target.value}))}
                    style={{...inp,fontSize:12,background:C.panel}}
                  />
                </div>;
              })}
            </div>}

            {(gapData.questions||[]).length===0&&<div style={{background:C.greenSoft,border:`1px solid ${C.green}30`,borderRadius:8,padding:"13px 16px",marginTop:8}}>
              <div style={{fontSize:13,fontWeight:600,color:C.green}}>✓ Your prompt is well-formed! No critical gaps detected.</div>
              <div style={{fontSize:11.5,color:C.textSub,marginTop:4}}>Click "Optimise with Context" to generate the 3 production-grade variants.</div>
            </div>}
          </div>}

          {/* ── OPTIMIZING ── */}
          {phase==="optimizing"&&<div style={{display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",height:"100%",gap:14}}>
            <Spinner size={36} color={C.accent}/>
            <div style={{fontSize:14,fontWeight:600,color:C.text}}>Generating optimised variants…</div>
            <div style={{fontSize:12,color:C.textSub}}>{FRAMEWORKS.find(f=>f.id===framework)?.label} · {selModel.label}</div>
          </div>}

          {/* ── RESULTS ── */}
          {phase==="results"&&result&&<div>
            {/* Analysis banner */}
            <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:10,padding:"13px 16px",marginBottom:14}}>
              <div style={{fontSize:9.5,fontWeight:700,color:C.textDim,letterSpacing:"1px",textTransform:"uppercase",marginBottom:10}}>📊 Optimisation Report</div>
              <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:14}}>
                <div>
                  <div style={{fontSize:9.5,color:C.textDim,fontWeight:700,textTransform:"uppercase",letterSpacing:"0.5px",marginBottom:6}}>Issues Fixed</div>
                  {(result.analysis?.detected_issues||[]).map((x,i)=><div key={i} style={{display:"flex",gap:5,fontSize:11,color:C.textSub,marginBottom:4,lineHeight:1.5}}><span style={{color:C.amber}}>⚠</span>{x}</div>)}
                </div>
                <div>
                  <div style={{fontSize:9.5,color:C.textDim,fontWeight:700,textTransform:"uppercase",letterSpacing:"0.5px",marginBottom:6}}>Result</div>
                  {result.analysis?.coverage_delta&&<div style={{fontSize:11,color:C.green,marginBottom:6,fontWeight:600}}>↑ {result.analysis.coverage_delta}</div>}
                  <div style={{fontSize:11,color:C.accent,marginBottom:5,lineHeight:1.5}}>{result.analysis?.framework_applied}</div>
                  {(result.techniques_applied||[]).length>0&&<div style={{display:"flex",flexWrap:"wrap",gap:4}}>
                    {result.techniques_applied.map(t=><span key={t} style={{background:C.orangeSoft,color:C.orange,border:`1px solid ${C.orange}30`,borderRadius:4,padding:"1px 7px",fontSize:10,fontWeight:600}}>{t}</span>)}
                  </div>}
                </div>
              </div>
            </div>
            <div style={{fontSize:10,fontWeight:700,color:C.textDim,letterSpacing:"0.8px",textTransform:"uppercase",marginBottom:10}}>3 Optimised Variants · read-only · click ✦ Refine to discuss in chat →</div>
            {(result.variants||[]).map((v,i)=><VariantCard key={v.id} variant={v} index={i} onRefine={handleRefine}/>)}
          </div>}
        </div>
      </div>

      {/* ─── RIGHT: Chat ─────────────────────────────────────── */}
      <div style={{width:chatOpen?380:46,flexShrink:0,background:C.surface,borderLeft:`1px solid ${C.border}`,display:"flex",flexDirection:"column",transition:"width 0.22s ease",overflow:"hidden"}}>
        {!chatOpen?(
          <button onClick={()=>setChatOpen(true)} title="Open AI Chat" style={{width:"100%",flex:1,background:"none",border:"none",color:C.textSub,cursor:"pointer",display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",gap:6}}>
            <span style={{fontSize:17}}>💬</span>
            <span style={{fontSize:9,fontWeight:700,letterSpacing:"0.8px",color:C.textDim,writingMode:"vertical-rl",textTransform:"uppercase"}}>AI Chat</span>
            {msgs.length>0&&<span style={{background:C.pink,color:"#fff",borderRadius:10,padding:"1px 6px",fontSize:10,fontWeight:700}}>{exchangeCount}</span>}
          </button>
        ):(
          <>
            {/* Chat header */}
            <div style={{padding:"0 13px",height:55,display:"flex",alignItems:"center",justifyContent:"space-between",borderBottom:`1px solid ${C.border}`,flexShrink:0}}>
              <div style={{display:"flex",alignItems:"center",gap:9}}>
                <div style={{width:26,height:26,background:`linear-gradient(135deg,${C.pink},${C.purple})`,borderRadius:6,display:"flex",alignItems:"center",justifyContent:"center",fontSize:13}}>✦</div>
                <div>
                  <div style={{fontSize:12.5,fontWeight:700,color:C.text}}>APOST Refiner</div>
                  <div style={{fontSize:10,color:C.textDim}}>{exchangeCount>0?`${exchangeCount} exchange${exchangeCount!==1?"s":""} · full memory`:"Seeded on optimisation"}</div>
                </div>
              </div>
              <div style={{display:"flex",gap:5}}>
                {msgs.length>0&&<button onClick={()=>{histRef.current=[];setMsgs([]);}} style={{background:C.panel,border:`1px solid ${C.border}`,borderRadius:5,color:C.textDim,fontSize:10,fontWeight:600,padding:"3px 8px",cursor:"pointer"}}>Clear</button>}
                <button onClick={()=>setChatOpen(false)} style={{background:C.panel,border:`1px solid ${C.border}`,borderRadius:5,color:C.textDim,fontSize:12,padding:"3px 8px",cursor:"pointer"}}>←</button>
              </div>
            </div>

            {/* Messages */}
            <div style={{flex:1,overflowY:"auto",padding:"12px",display:"flex",flexDirection:"column",gap:11}}>
              {msgs.length===0&&<div style={{textAlign:"center",padding:"22px 10px"}}>
                <div style={{fontSize:28,opacity:0.25,marginBottom:10}}>✦</div>
                <div style={{fontSize:12.5,fontWeight:600,color:C.text,marginBottom:7}}>Your prompt refinement coach</div>
                <div style={{fontSize:11.5,color:C.textSub,lineHeight:1.65,marginBottom:16}}>
                  {phase==="results"?"Chat context is loading…":"Run the optimiser — the full output will be posted here automatically so you can refine conversationally."}<br/><br/>
                  Or ask about prompt engineering techniques right now.
                </div>
                {phase!=="results"&&<div style={{display:"flex",flexDirection:"column",gap:5}}>
                  {["What is TCRTE and when do I use it?","Explain CoRe (Context Repetition)","What's the RAL-Writer restate technique?","When should I use Claude prefilling?"].map(q=>(
                    <button key={q} onClick={()=>sendChat(q)} style={{background:C.panel,border:`1px solid ${C.border}`,borderRadius:7,padding:"7px 10px",fontSize:11,color:C.textSub,cursor:"pointer",textAlign:"left",lineHeight:1.4}}>💬 {q}</button>
                  ))}
                </div>}
              </div>}
              {msgs.map((m,i)=><ChatBubble key={i} msg={m}/>)}
              {chatLoading&&<div style={{alignSelf:"flex-start",display:"flex",alignItems:"center",gap:8,padding:"8px 12px",background:C.panel,border:`1px solid ${C.border}`,borderRadius:"11px 11px 11px 3px"}}>
                <Spinner size={12} color={C.pink}/><span style={{fontSize:11.5,color:C.textSub}}>Thinking…</span>
              </div>}
              <div ref={endRef}/>
            </div>

            {/* Quick actions */}
            {phase==="results"&&msgs.length>0&&<div style={{padding:"8px 13px 5px",borderTop:`1px solid ${C.border}`,flexShrink:0}}>
              <div style={{fontSize:9,color:C.textDim,fontWeight:700,letterSpacing:"0.6px",textTransform:"uppercase",marginBottom:5}}>Quick Actions</div>
              <div style={{display:"flex",flexWrap:"wrap",gap:4}}>
                {QUICK_ACTIONS.map(a=>(
                  <button key={a.label} onClick={()=>sendChat(a.label)}
                    onMouseEnter={e=>{e.currentTarget.style.borderColor=C.pink;e.currentTarget.style.color=C.pink;}}
                    onMouseLeave={e=>{e.currentTarget.style.borderColor=C.border;e.currentTarget.style.color=C.textDim;}}
                    style={{background:C.panel,border:`1px solid ${C.border}`,borderRadius:13,padding:"3px 9px",fontSize:10.5,color:C.textDim,cursor:"pointer",transition:"all 0.12s",whiteSpace:"nowrap"}}>
                    {a.icon} {a.label}
                  </button>
                ))}
              </div>
            </div>}

            {/* Input */}
            <div style={{padding:"10px 13px 12px",borderTop:`1px solid ${C.border}`,display:"flex",flexDirection:"column",gap:6,flexShrink:0}}>
              <div style={{display:"flex",gap:7,alignItems:"flex-end"}}>
                <textarea ref={inputRef} rows={2}
                  placeholder={phase==="results"?"Refine a variant, add guards, change tone…":"Ask about prompt engineering…"}
                  value={chatInput} onChange={e=>setChatInput(e.target.value)}
                  onKeyDown={e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();sendChat();}}}
                  style={{flex:1,background:C.panel,border:`1px solid ${C.border}`,borderRadius:8,color:C.text,fontFamily:C.sans,fontSize:12.5,padding:"8px 11px",resize:"none",outline:"none",lineHeight:1.5,maxHeight:100,overflowY:"auto",boxSizing:"border-box"}}/>
                <button onClick={()=>sendChat()} disabled={chatLoading||!chatInput.trim()}
                  style={{background:(chatLoading||!chatInput.trim())?C.borderHi:`linear-gradient(135deg,${C.pink},${C.purple})`,border:"none",borderRadius:8,color:"#fff",width:36,height:36,cursor:(chatLoading||!chatInput.trim())?"not-allowed":"pointer",display:"flex",alignItems:"center",justifyContent:"center",flexShrink:0,fontSize:16}}>
                  {chatLoading?<Spinner size={13}/>:"↑"}
                </button>
              </div>
              <div style={{fontSize:9.5,color:C.textDim,textAlign:"center"}}>Enter ↵ to send · Shift+Enter new line{msgs.length>0?` · ${msgs.length} msgs in memory`:""}</div>
            </div>
          </>
        )}
      </div>
    </div>

    <style>{`
      *{box-sizing:border-box;}
      textarea:focus,input:focus,select:focus{border-color:${C.accent}!important;}
      ::-webkit-scrollbar{width:5px;}
      ::-webkit-scrollbar-track{background:transparent;}
      ::-webkit-scrollbar-thumb{background:${C.borderHi};border-radius:3px;}
      select option{background:${C.panel};}
    `}</style>
  </div>;
}
