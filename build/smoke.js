/* 연기 시험 — 최소 DOM 흉내로 페이지 스크립트를 통째로 실행한다.
 *
 * 문법 검사(node --check)로는 못 잡는 것들을 잡는다:
 *  - 선언보다 먼저 쓰는 변수 (TDZ ReferenceError). 실제로 이것 때문에 입장 버튼이 죽은 적이 있다.
 *  - 마크업에 없는 id 를 getElementById 로 잡아 쓰는 경우
 *  - 초기화 중에 터지는 예외 전반
 *
 * 쓰는 법:  node build/smoke.js [costume-graph.html 경로]
 * 실패하면 종료코드 1 — CI 에서 배포를 막는 데 쓴다.
 */
const fs=require('fs');
const target=process.argv[2]||require('path').join(__dirname,'..','costume-graph.html');
const html=fs.readFileSync(target,'utf8');
const ids=[...html.matchAll(/id="([^"]+)"/g)].map(m=>m[1]);

const noop=()=>{};
const ctxStub=new Proxy({},{get:(t,p)=>{
  if(p==='measureText') return ()=>({width:40});
  if(p==='canvas') return {width:1200,height:800};
  if(['fillStyle','strokeStyle','lineWidth','font','globalAlpha','textAlign','textBaseline','lineCap'].includes(p)) return t[p];
  return noop;
},set:(t,p,v)=>{t[p]=v;return true;}});

const listeners={};
function mkEl(id){
  const el={
    id, hidden:false, value:'', textContent:'', innerHTML:'', style:{}, dataset:{},
    children:[], min:0,max:0,step:1,
    classList:{ _s:new Set(), add(c){this._s.add(c)}, remove(c){this._s.delete(c)},
                toggle(c,v){v?this._s.add(c):this._s.delete(c)}, contains(c){return this._s.has(c)} },
    getContext:()=>ctxStub, clientWidth:1200, clientHeight:800, width:1200, height:800,
    addEventListener:(t,f)=>{ (listeners[id+':'+t] ||= []).push(f); },
    setPointerCapture:noop, setAttribute(k,v){ this[k]=v; },
    getBoundingClientRect:()=>({width:100,height:30,left:0,top:0}),
    appendChild(c){ this.children.push(c); },
    querySelectorAll:()=>[],
    scrollTop:0, focus:noop, blur:noop,
  };
  return el;
}
const store={}; ids.forEach(i=>store[i]=mkEl(i));
global.document={
  getElementById:id=>store[id]||null,
  createElement:()=>mkEl('new'),
  documentElement:{dataset:{},style:{}},
  fonts:{ready:Promise.resolve()},
  addEventListener:noop,
};
global.getComputedStyle=()=>({getPropertyValue:v=>({'--ground':'#EDE6D8','--ink':'#1F1A16','--ink-2':'#59504A',
  '--ink-3':'#8A7F70','--brand':'#D81818','--panel':'#F6F1E7','--edge':'#C7BCA4','--seam':'rgba(31,26,22,.32)',
  '--p0':'#2F4FA8','--p1':'#B2352B','--p2':'#35785A','--p3':'#9C7315','--p4':'#6B4A93',
  '--p5':'#1F7180','--p6':'#B04A75','--p7':'#6E6524','--p8':'#4A4038','--p9':'#B2551E'}[v]||'#000000')});
global.matchMedia=()=>({matches:false});
global.devicePixelRatio=2; global.innerWidth=1200; global.innerHeight=800;
global.Path2D=class{ moveTo(){} lineTo(){} closePath(){} };
// 낡은 사파리처럼 roundRect 가 없는 캔버스. 페이지가 넣는 폴리필이 여기서 걸린다.
global.CanvasRenderingContext2D=class{};
// 자기 갱신 경로를 타되 바깥으로 나가지는 않게. 연기 시험은 네트워크를 쓰지 않는다.
// (node 18+ 에는 진짜 fetch 가 있어서 막지 않으면 실제로 접속하러 나간다)
global.AbortController=class{ constructor(){ this.signal={aborted:false}; } abort(){ this.signal.aborted=true; } };
global.fetch=()=>Promise.reject(new Error('연기 시험에는 네트워크가 없다'));
global.requestAnimationFrame=()=>0;
global.addEventListener=(t,f)=>{ (listeners['win:'+t] ||= []).push(f); };
const timers=[];
global.setTimeout=(f,ms)=>{ timers.push({f,ms}); return timers.length; };
global.clearTimeout=noop;
function runTimers(){ const q=timers.splice(0).sort((a,b)=>a.ms-b.ms); q.forEach(t=>{ try{t.f();}catch(e){} }); }
global.navigator={platform:'MacIntel'};
global.window={top:{},self:{}};

const js=html.split('<script>')[1].split('</script>')[0];
try{
  new Function(js)();
  console.log('✔ 스크립트 전체 실행 통과 (예외 없음)');
}catch(e){
  console.log('✘ 실행 중 예외:', e.constructor.name, '-', e.message);
  console.log(e.stack.split('\n').slice(0,4).join('\n'));
  process.exit(1);
}
const enter=store['enter'];
console.log('입장 버튼 onclick 붙었나:', typeof enter.onclick==='function' ? '예' : '아니오 ← 문제');
console.log('gateStat 채워졌나:', store['gateStat'].textContent ? `예 ("${store['gateStat'].textContent}")` : '아니오');
console.log('통계 채워졌나: 키워드', store['t-k'].textContent, '/ 논문', store['t-p'].textContent, '/ 연구자', store['t-a'].textContent);
console.log('갈래 목록 항목 수:', store['fieldList'].children.length);
if(typeof enter.onclick==='function'){ enter.onclick(); console.log('입장 클릭 실행:', store['gate'].classList.contains('open')?'대문 열림 ✔':'변화 없음 ✘'); }

/* 첫 안내 — 들어가면 뜨고, 굴리면 사라져야 한다 */
const hintProblems=[];
{
  const hb=store['hintBox'];
  if(hb.classList.contains('on')) hintProblems.push('입장 전인데 안내가 떠 있다');
  runTimers();                                   // 입장 클릭이 걸어둔 타이머를 돌린다
  if(!hb.classList.contains('on')) hintProblems.push('입장 후에도 안내가 안 뜬다');
  if(!store['hintMain'].textContent) hintProblems.push('안내 문구가 비었다');
  else console.log('첫 안내 문구:', store['hintMain'].textContent);
  const wheels=listeners['cv:wheel']||[];
  if(!wheels.length) hintProblems.push('휠 핸들러가 없다');
  else {
    wheels.forEach(f=>f({deltaY:-100,deltaMode:0,offsetX:400,offsetY:300,clientX:400,clientY:300,
                         preventDefault(){},ctrlKey:false,metaKey:false}));
    if(hb.classList.contains('on')) hintProblems.push('스크롤해도 안내가 안 사라진다');
  }
}
console.log('첫 안내:', hintProblems.length ? '✘ '+hintProblems.join(' / ') : '정상');

/* 검색 -> 지도 자취 — 사용자가 실제로 쓰는 경로를 짚는다 */
function fireSearch(term){
  const q=store['q']; q.value=term;
  const fns=listeners['q:input']||[];
  if(!fns.length) return '검색 입력 핸들러가 없다';
  fns.forEach(f=>f({}));
  return null;
}
const searchProblems=[];
{
  const err=fireSearch('이유리');
  if(err) searchProblems.push(err);
  else {
    const tb=store['traceBar'];
    if(!tb.innerHTML.includes('이유리')) searchProblems.push('연구자 검색 시 자취 띠가 안 뜬다');
    if(!tb.classList.contains('on')) searchProblems.push('자취 띠가 켜지지 않는다');
    if(!store['k-body'].innerHTML.includes('이유리')) searchProblems.push('검색 결과 카드가 비었다');
    console.log('연구자 검색(이유리) 자취 띠:', tb.innerHTML.replace(/<[^>]+>/g,' ').trim() || '(빈값)');
  }
  fireSearch('한복');
  if(!store['k-body'].innerHTML.includes('한복')) searchProblems.push('키워드 검색 결과가 비었다');
  fireSearch('');
  if(store['traceBar'].classList.contains('on')) searchProblems.push('검색어를 지워도 자취가 남는다');
}
console.log('검색 경로:', searchProblems.length ? '✘ '+searchProblems.join(' / ') : '정상');

const bad=[];
bad.push(...searchProblems, ...hintProblems);
if(typeof enter.onclick!=='function') bad.push('입장 버튼에 핸들러가 없다');
if(!store['gateStat'].textContent) bad.push('대문 통계가 비었다');
if(!store['t-k'].textContent || store['t-k'].textContent==='0') bad.push('키워드 수가 비었다');
if(store['fieldList'].children.length<3) bad.push('갈래 목록이 비었다');
if(bad.length){ console.log('\n✘ ' + bad.join('\n✘ ')); process.exit(1); }
console.log('\n✔ 연기 시험 통과');
