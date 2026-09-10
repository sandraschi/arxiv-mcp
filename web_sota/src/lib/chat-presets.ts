/** Per-repo chat prompt presets (arxiv-mcp: research workflows).
 *
 * PRESET FILE CONTRACT (fleet template rule): this file is PER-REPO DATA.
 * Never vendor it — each repo writes its own presets for its own domain.
 * Template ships the TYPE + 2 generic examples only (see
 * mcp-central-docs/templates/chat/). Shape: id/label/prompt. Selecting a
 * preset fills the input box (replaces when empty, appends otherwise);
 * prompts end with an open cue so the user pastes content after them.
 */

export interface ChatPreset {
  id: string;
  label: string;
  prompt: string;
}

export const CHAT_PRESETS: ChatPreset[] = [
  {
    id: "deep-read",
    label: "Paper deep-read",
    prompt:
      "Deep-read the paper below adversarially. 1) One-paragraph summary. 2) Core claims as bullets. 3) Strongest evidence per claim. 4) Weakest link: methods, controls, or stats most likely to break. 5) What single experiment would change your mind?\n\nPAPER:\n",
  },
  {
    id: "related-work",
    label: "Related-work scan",
    prompt:
      "Given the abstract below, map the related-work landscape: 1) closest prior art (3-5 works), 2) what this adds over each, 3) what it conspicuously does not cite, 4) independent corroboration or contradiction you know of.\n\nABSTRACT:\n",
  },
  {
    id: "methods-critique",
    label: "Methods critique",
    prompt:
      "Stress-test the methods below: sample sizes and power, ablations present vs missing, baselines (are they current SOTA or strawmen?), compute budget vs claims, reproducibility gaps. End with a verdict: accept / revise / reject with reasons.\n\nMETHODS:\n",
  },
  {
    id: "explain-simply",
    label: "Explain simply",
    prompt:
      "Explain the following like I'm a smart undergrad outside the field. No jargon without definition. One concrete analogy. Then one paragraph on why anyone should care.\n\nTEXT:\n",
  },
  {
    id: "citation-hunt",
    label: "Citation hunt",
    prompt:
      "For the claim below, find supporting and contradicting evidence: 1) strongest supporting work, 2) strongest contradicting work, 3) your calibrated take on which way the evidence leans and why.\n\nCLAIM:\n",
  },
];
