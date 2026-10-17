"use strict";
// This interface is a scripted preview. No calls to production or staging APIs.
const $ = (s, root = document) => root.querySelector(s);
const $$ = (s, root = document) => Array.from(root.querySelectorAll(s));
const state = {
  page: "overview", legendReceived: false, pilotUsed: 1, zoom: 1, selected: "p101",
  objectFilter: "all", chatOpen: false, selectedReview: 0,
  resolvedReviews: new Set()
};
const objects = {
  v101: { title: "V-101 · Feed vessel", type: "Equipment candidate", ref: "V-101", box: "X: 104–255 · Y: 160–365", confidence: "Vessel outline · unverified", links: "2 nearby CAD strokes", question: "Confirm vessel tag and distinguish feed nozzle from utility connection." },
  p101: { title: "P-101 · Transfer pump", type: "Equipment candidate", ref: "P-101", box: "X: 449–533 · Y: 239–323", confidence: "Pump shape proposal · unverified", links: "2 nearby CAD strokes", question: "Pump shape detected; confirm equipment identifier and suction/discharge connections." },
  e101: { title: "E-101 · Process cooler", type: "Equipment candidate", ref: "E-101", box: "X: 809–893 · Y: 241–321", confidence: "Equipment geometry · unverified", links: "2 nearby CAD strokes", question: "Confirm exchanger type, nozzle connections and drawing reference." },
  hv101: { title: "HV-101 · Hand valve", type: "Valve candidate", ref: "HV-101", box: "X: 329–367 · Y: 264–299", confidence: "Valve family proposal · unverified", links: "2 line segments nearby", question: "Confirm exact valve symbol and normal position using the approved project legend." },
  xv102: { title: "XV-102 · Actuated valve", type: "Valve candidate", ref: "XV-102", box: "X: 655–691 · Y: 217–300", confidence: "Valve + actuator shape · unverified", links: "2 line segments nearby", question: "Confirm valve function, actuator type and control signal association." },
  ft101: { title: "FT-101 · Flow transmitter", type: "Instrument candidate", ref: "FT-101", box: "X: 588–642 · Y: 150–204", confidence: "Instrument bubble · unverified", links: "1 signal-line candidate", question: "Confirm transmitter tag, symbol enclosure and sensing location." },
  lt101: { title: "LT-101 · Level transmitter", type: "Instrument candidate", ref: "LT-101", box: "X: 268–318 · Y: 198–248", confidence: "Instrument bubble · unverified", links: "1 proximity attachment", question: "Verify if this LT attaches to the vessel nozzle and which tapping is intended." },
  pl101: { title: "6\"-CW-1001 · Candidate line", type: "Piping text observation", ref: "6\"-CW-1001", box: "X: 541–609 · Y: 260–281", confidence: "Tag text only · not associated", links: "Line identity unassigned", question: "Review the original drawing to prove which continuous CAD route this line tag identifies." },
  junction: { title: "Junction J? · Unresolved", type: "Geometric branch candidate", ref: "J?", box: "X: 979–1013 · Y: 265–304", confidence: "Tee/cross ambiguous", links: "2 crossing/branch candidates", question: "Does the vertical segment join the process line or cross it without connection?" }
};
const reviews = [
  { ref: "J-004", title: "Crossing or tee?", type: "Piping topology", question: "Does the vertical connection downstream of the cooler form a tee to the drain, or is it a non-connected crossing?", item: "junction" },
  { ref: "V-014", title: "Confirm valve symbol", type: "Valve recognition", question: "Verify the XV-102 symbol class, actuator and normal position against the client-approved legend.", item: "xv102" },
  { ref: "P-003", title: "Confirm pump ports", type: "Equipment connection", question: "Are both nearby CAD lines correctly attached to pump P-101 suction and discharge ports?", item: "p101" },
  { ref: "I-011", title: "Instrument connection", type: "Instrument recognition", question: "Is FT-101 connected as a flow transmitter to the correct line, and does the approved legend support this enclosure?", item: "ft101" }
];
function showPage(name) {
  if (!$( `.page[data-page="${name}"]`)) return;
  state.page = name;
  $$(".page").forEach(el => el.classList.toggle("active", el.dataset.page === name));
  $$(".nav-link").forEach(el => el.classList.toggle("active", el.dataset.nav === name));
  $("#sidebar").classList.remove("open"); $("#mobileBackdrop").classList.remove("open");
  window.scrollTo({ top: 0, behavior: "instant" });
}
function selectObject(id) {
  if (!objects[id]) return;
  state.selected = id; const item = objects[id];
  $("#inspectTitle").textContent = item.title;
  $("#inspectType").textContent = item.type;
  $("#inspectRef").textContent = item.ref;
  $("#inspectCoords").textContent = item.box;
  $("#inspectConfidence").textContent = item.confidence;
  $("#inspectConnected").textContent = item.links;
  $("#inspectQuestion").textContent = item.question;
  $("#inspectReviewQuestion").textContent = item.question;
  $$(".pid-item,.graph-node").forEach(el => el.classList.toggle("active", el.dataset.item === id));
}
function selectObjectFilter(filter) {
  state.objectFilter = filter;
  $$("[data-object-filter]").forEach(el => el.classList.toggle("selected", el.dataset.objectFilter === filter));
  $$(".pid-item").forEach(el => { const isFiltered = filter !== "all" && el.dataset.objectType !== filter; el.style.opacity = isFiltered ? ".26" : "1"; });
}
function updateQuota() {
  $("#quotaUsedSide").textContent = state.pilotUsed;
  $("#quotaUsedOverview").textContent = state.pilotUsed;
  $("#quotaProgressSide").style.width = `${state.pilotUsed / 2 * 100}%`;
}
function updateIntake() {
  $("#intakeQuestion").classList.toggle("hidden", state.legendReceived);
  $("#intakeSuccess").classList.toggle("hidden", !state.legendReceived);
  $("#legendStatusBadge").textContent = state.legendReceived ? "✓ Matched" : "Missing";
  $("#legendStatusBadge").classList.toggle("warning", !state.legendReceived);
  $("#legendUploadDescription").textContent = state.legendReceived ? "cw_pid_legend.pdf · synthetic example · 1 sheet" : "Not yet received in this workflow simulation";
  $("#intakeLegendStep").classList.toggle("done", state.legendReceived);
  $("#intakeLegendStep").classList.toggle("current", !state.legendReceived);
  $("#intakeReadyStep").classList.toggle("current", state.legendReceived);
  $("#legendHandoff").textContent = state.legendReceived ? "✓" : "?";
  $("#legendHandoff").classList.toggle("green", state.legendReceived);
  $("#completenessState").textContent = state.legendReceived ? "Legend presence confirmed" : "Waiting for legend";
}
function updateZoom() {
  $("#canvasStage").style.setProperty("--zoom", state.zoom);
  $("#zoomLabel").textContent = `${Math.round(state.zoom * 100)}%`;
}
function renderReviews() {
  const parent = $("#reviewItems"); parent.replaceChildren();
  reviews.forEach((entry, i) => {
    const done = state.resolvedReviews.has(i);
    const button = document.createElement("button"); button.type = "button";
    button.className = `review-item${state.selectedReview === i ? " active" : ""}${done ? " resolved" : ""}`;
    button.innerHTML = `<span class="review-number">${done ? "✓" : i + 1}</span><div><strong></strong><p></p></div><span class="item-arrow">›</span>`;
    $("strong", button).textContent = entry.title + (done ? " · simulated review" : "");
    $("p", button).textContent = entry.ref + "  •  " + entry.type;
    button.addEventListener("click", () => { state.selectedReview = i; updateReviewDetail(); renderReviews(); });
    parent.appendChild(button);
  });
  const count = reviews.length - state.resolvedReviews.size;
  $("#reviewCountPage").textContent = count;
  $("#reviewCountNav").textContent = count;
}
function updateReviewDetail() {
  const entry = reviews[state.selectedReview];
  $("#reviewDetailTitle").textContent = entry.title;
  $("#reviewDetailQuestion").textContent = entry.question;
  $("#simulateResolve").textContent = state.resolvedReviews.has(state.selectedReview) ? "Reset simulated decision" : "Mark reviewed (demo)";
  selectObject(entry.item);
}
function openChat(message) {
  state.chatOpen = true;
  $("#chatWidget").classList.add("open"); $("#chatWidget").setAttribute("aria-hidden", "false");
  if (message) addChatMessage("agent", message);
  $("#chatText").focus();
}
function closeChat() {
  state.chatOpen = false; $("#chatWidget").classList.remove("open"); $("#chatWidget").setAttribute("aria-hidden", "true");
}
function addChatMessage(who, content) {
  const div = document.createElement("div"); div.className = `chat-bubble ${who}`;
  div.textContent = content; $("#chatStream").appendChild(div);
  $("#chatStream").scrollTop = $("#chatStream").scrollHeight;
}
function scriptedResponse(question) {
  const q = question.toLowerCase();
  if (/legend|missing/.test(q)) return "The Completeness Agent checks for the project-specific P&ID legend. If it is missing or ambiguous, the workflow pauses and asks the client to provide or clarify it. You can simulate this in Client onboarding.";
  if (/quota|free|two|2 |sales|price|commercial|drawing/.test(q)) return `The free pilot allows two P&ID reservations per company. This synthetic demo shows ${state.pilotUsed} used. Further conversions require a commercial agreement and authorized credits.`;
  if (/graph|pipe|connect|approved|tee|cross/.test(q)) return "Geometry and visual proximity are not confirmed engineering piping connections. The Review Agent flags tees, crossings, source tags and ports; physical graph edges remain unapproved until an engineer validates them.";
  if (/privacy|private|training|model|learn/.test(q)) return "Client data is excluded from global model training by default. Private-cloud client data must never train our shared models. Production isolation still requires independent security validation.";
  if (/symbol|valve|pump|recogn/.test(q)) return "The recognition worker generates source-linked geometry and symbol-family proposals for engineer review. Exact legend matching and real refinery recognition accuracy are still pending.";
  return "This is a scripted preview, so I cannot inspect real files or invoke the live agents here. Explore P&ID digitalization, the graph and Review queue from the navigation. What would you like to check next?";
}
function downloadEquipmentCSV() {
  const csv = "TAG,DESCRIPTION,TYPE,STATUS,SOURCE\nV-101,Feed vessel,Vertical vessel,UNREVIEWED,Synthetic CW-101\nP-101,Transfer pump,Centrifugal pump,UNREVIEWED,Synthetic CW-101\nE-101,Process cooler,Heat exchanger,UNREVIEWED,Synthetic CW-101\n";
  const url = URL.createObjectURL(new Blob([csv], {type:"text/csv;charset=utf-8"}));
  const link = document.createElement("a"); link.href = url; link.download = "synthetic-equipment-register-unreviewed.csv";
  document.body.appendChild(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function attachEvents() {
  $$('[data-nav],[data-jump]').forEach(el => el.addEventListener("click", () => showPage(el.dataset.nav || el.dataset.jump)));
  $("#menuToggle").addEventListener("click", () => { $("#sidebar").classList.add("open"); $("#mobileBackdrop").classList.add("open"); });
  $("#mobileBackdrop").addEventListener("click", () => { $("#sidebar").classList.remove("open"); $("#mobileBackdrop").classList.remove("open"); });
  $$('[data-item]').forEach(el => {el.addEventListener("click", () => selectObject(el.dataset.item));el.addEventListener("keydown", e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();selectObject(el.dataset.item);}});});
  $$('[data-object-filter]').forEach(el => el.addEventListener("click", () => selectObjectFilter(el.dataset.objectFilter)));
  $("#toggleAnnotations").addEventListener("change", e => {$("#annotationLayer").style.display = e.target.checked ? "" : "none";});
  $("#zoomOut").addEventListener("click", () => { state.zoom = Math.max(.7, state.zoom - .15); updateZoom(); });
  $("#zoomIn").addEventListener("click", () => { state.zoom = Math.min(1.6, state.zoom + .15); updateZoom(); });
  $("#zoomReset").addEventListener("click", () => { state.zoom = 1; updateZoom(); });
  $$('[data-inspector-tab]').forEach(el => el.addEventListener("click", () => {
    $$(".inspector-tab").forEach(button => button.classList.toggle("active", button === el));
    $$(".inspector-tab-body").forEach(body => body.classList.toggle("active", body.dataset.inspectorBody === el.dataset.inspectorTab));
  }));
  $("#openReviewFromViewer").addEventListener("click", () => showPage("review"));
  $("#addDemoLegend").addEventListener("click", () => {state.legendReceived = true;updateIntake();openChat("The synthetic project legend has been attached. The Completeness Agent may now pass this demo document to recognition; engineering classification still needs approval.");});
  $("#resetDemoIntake").addEventListener("click", () => {state.legendReceived=false;updateIntake();});
  $("#simulateResolve").addEventListener("click", () => {const id=state.selectedReview;state.resolvedReviews.has(id)?state.resolvedReviews.delete(id):state.resolvedReviews.add(id);updateReviewDetail();renderReviews();});
  $("#askAgent").addEventListener("click", () => openChat(scriptedResponse(reviews[state.selectedReview].question)));
  $("#exportEquipment").addEventListener("click", downloadEquipmentCSV);
  $("#chatToggle").addEventListener("click", () => state.chatOpen ? closeChat() : openChat());
  $("#chatClose").addEventListener("click", closeChat);
  $$('[data-chat]').forEach(el => el.addEventListener("click", () => {const q=el.dataset.chat;addChatMessage("client",q);addChatMessage("agent",scriptedResponse(q));}));
  $("#chatForm").addEventListener("submit", e => {e.preventDefault();const input=$("#chatText");const q=input.value.trim();if(!q)return;addChatMessage("client",q);addChatMessage("agent",scriptedResponse(q));input.value="";});
  document.addEventListener("keydown", e=>{if(e.key==="Escape"){closeChat();$("#sidebar").classList.remove("open");$("#mobileBackdrop").classList.remove("open");}});
}
updateQuota();updateIntake();updateReviewDetail();renderReviews();selectObject("p101");attachEvents();