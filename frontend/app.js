(function(){
"use strict";
var $=function(id){return document.getElementById(id)};
var LABELS=["friendly","neutral","passive-aggressive","angry","anxious"];
var msg=$("msg"),banner=$("banner"),send=$("send"),status=$("status");
var timer=null,ctrl=null,risk=0,seq=0;

var bars=$("bars");
LABELS.forEach(function(l){
  var li=document.createElement("li");
  li.innerHTML='<span></span><div class="b"><i></i></div><span class="n">0%</span>';
  li.children[0].textContent=l;li.querySelector("i").style.background="var(--"+l+")";
  li.dataset.l=l;bars.appendChild(li);
});

function setStatus(t,cls){
  if(!t){status.hidden=true;return}
  status.hidden=false;status.textContent=t;status.className="status "+(cls||"");
}
function pct(x){return Math.round(Math.max(0,Math.min(1,x))*100)}

function render(d){
  var tone=d.tone||{},sc=tone.scores||{};
  $("pill").textContent=tone.label||"neutral";
  $("pill").dataset.tone=tone.label||"neutral";
  $("conf").textContent=pct(tone.confidence||0)+"% confident";
  Array.prototype.forEach.call(bars.children,function(li){
    var v=sc[li.dataset.l]||0;
    li.querySelector("i").style.width=pct(v)+"%";
    li.querySelector(".n").textContent=pct(v)+"%";
  });
  var f=d.formality&&typeof d.formality.score==="number"?Math.max(1,Math.min(5,d.formality.score)):3;
  $("formVal").textContent=f.toFixed(1)+" / 5";
  $("formDot").style.left=((f-1)/4*100)+"%";
  risk=Math.max(0,Math.min(1,d.fight_risk||0));
  $("riskVal").textContent=pct(risk)+"%";
  var col=risk>0.6?"var(--bad)":risk>0.35?"var(--warn)":"var(--good)";
  $("mercury").style.width=pct(risk)+"%";$("mercury").style.background=col;$("bulb").style.background=col;
  banner.hidden=!(risk>0.6);
  send.classList.toggle("calm",risk<=0.35&&!!msg.value.trim());
  var L=d.language;
  if(L&&msg.value.trim()){$("langFlag").textContent=L.flag||"";$("langName").textContent=L.name||L.code||"";$("lang").hidden=false}
  else $("lang").hidden=true;
}

function reset(){
  render({tone:{label:"neutral",confidence:0,scores:{}},formality:{score:3},fight_risk:0});
  $("formVal").textContent="–";$("conf").textContent="–";
  setStatus("Start typing to see how your message reads.","info");
}

function analyze(){
  var text=msg.value;
  if(ctrl)ctrl.abort();
  if(!text.trim()){reset();return}
  ctrl=new AbortController();var my=++seq;
  fetch("/analyze",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({text:text}),signal:ctrl.signal})
  .then(function(r){if(!r.ok)throw new Error("HTTP "+r.status);return r.json()})
  .then(function(d){if(my!==seq)return;setStatus("");render(d)})
  .catch(function(e){
    if(e&&e.name==="AbortError")return;
    if(my!==seq)return;
    setStatus("Can't reach the analysis server. Check that it's running and try again.");
  });
}

msg.addEventListener("input",function(){
  $("count").textContent=msg.value.length+" chars";
  clearTimeout(timer);timer=setTimeout(analyze,150);
});

function fallbackCopy(t){
  var a=document.createElement("textarea");a.value=t;a.style.position="fixed";a.style.opacity="0";
  document.body.appendChild(a);a.select();var ok=false;
  try{ok=document.execCommand("copy")}catch(e){}
  document.body.removeChild(a);return ok;
}
send.addEventListener("click",function(){
  var t=msg.value;if(!t.trim())return;
  var done=function(ok){
    var old="Copy & Send";send.textContent=ok?"Copied ✓":"Copy failed";
    setTimeout(function(){send.textContent=old},1500);
  };
  if(navigator.clipboard&&navigator.clipboard.writeText)
    navigator.clipboard.writeText(t).then(function(){done(true)},function(){done(fallbackCopy(t))});
  else done(fallbackCopy(t));
});

reset();
})();
