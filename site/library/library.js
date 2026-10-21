'use strict';
const $=id=>document.getElementById(id), ids=['query','kind','topic','source','from','to'];
let manifest, rows=[], matches=[], shown=0, generation=0, ready=false;
const cache=new Map(), normalize=s=>s.normalize('NFKC').toLocaleLowerCase();
const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
function link(text,url){const a=el('a',text);a.href=url;return a;}
async function get(url){const r=await fetch(url,{cache:'no-cache'});if(!r.ok)throw Error(String(r.status));return r.json();}
function options(id,values){const selected=$(id).value;$(id).replaceChildren(new Option(id==='topic'?'모든 주제':'모든 출처',''));for(const v of [...new Set(values)].filter(Boolean).sort((a,b)=>a.localeCompare(b,'ko')))$(id).add(new Option(v,v));if(selected&&!values.includes(selected))$(id).add(new Option(selected,selected));$(id).value=selected;}
function save(){const p=new URLSearchParams();for(const id of ids)if($(id).value)p.set(id,$(id).value);history.replaceState(null,'',location.pathname+(p.size?'?'+p:''));}
function card(r){const c=el('article',undefined,'card');const top=el('div',undefined,'meta');top.append(el('span',r.kind==='news'?'뉴스':'GeekNews','badge '+r.kind),el('span',r.appearances[0].date),el('span',r.sources.join(' · ')));c.append(top);const h=el('h3');h.append(link(r.title,r.appearances[0].url));c.append(h);if(r.topics.length)c.append(el('p',r.topics.join(' · '),'tags'));if(r.body.length)c.append(el('p',r.body[0],'lead'));if(r.body.length>1){const detail=el('details');detail.append(el('summary','브리핑 내용 전체 보기'));for(const text of r.body.slice(1))detail.append(el('p',text));c.append(detail);}const links=el('div',undefined,'links');links.append(link('브리핑 읽기 ↗',r.appearances[0].url));r.links.forEach((url,i)=>{const a=link(r.links.length===1?'원문 ↗':'원문 '+(i+1)+' ↗',url);a.target='_blank';a.rel='noopener noreferrer';links.append(a);});c.append(links);if(r.appearances.length>1){const p=el('div','게재 날짜 · ','appearances');for(const a of r.appearances)p.append(link(a.date,a.url));c.append(p);}return c;}
function more(){const next=matches.slice(shown,shown+30);$('results').append(...next.map(card));shown+=next.length;$('more').hidden=shown>=matches.length;}
function filter(){if(!ready)return;save();const terms=normalize($('query').value.trim()).split(/\s+/).filter(Boolean);matches=rows.filter(r=>(!$('kind').value||r.kind===$('kind').value)&&(!$('topic').value||r.topics.includes($('topic').value))&&(!$('source').value||r.sources.includes($('source').value))&&terms.every(t=>r.search.includes(t)));$('results').replaceChildren();shown=0;$('result-count').textContent=matches.length.toLocaleString()+'개 결과';$('status').textContent=matches.length?'':'조건에 맞는 브리핑이 없습니다. 검색어나 기간을 바꿔 보세요.';more();}
async function load(){ready=false;rows=[];const current=++generation;$('retry').hidden=true;$('results').replaceChildren();$('more').hidden=true;$('status').textContent='브리핑을 불러오는 중…';$('result-count').textContent='불러오는 중';try{if(!manifest)manifest=await get('catalog.json');const from=$('from').value,to=$('to').value;if(from&&to&&from>to){$('status').textContent='시작일을 종료일보다 앞선 날짜로 선택해 주세요.';$('result-count').textContent='기간 확인 필요';return;}
$('totals').textContent=manifest.edition_count+'개 브리핑 · 뉴스 '+manifest.counts.news.toLocaleString()+'건 · GeekNews '+manifest.counts.geeknews.toLocaleString()+'건 게재';const months=manifest.months.filter(m=>(!from||m.month>=from.slice(0,7))&&(!to||m.month<=to.slice(0,7)));const gathered=[];let cursor=0;await Promise.all(Array.from({length:Math.min(3,months.length)},async()=>{while(cursor<months.length){const m=months[cursor++];if(!cache.has(m.file))cache.set(m.file,await get(m.file));gathered.push(...cache.get(m.file));}}));if(current!==generation)return;const grouped=new Map();for(const r of gathered){const appearances=r.appearances.filter(a=>(!from||a.date>=from)&&(!to||a.date<=to));if(!appearances.length)continue;if(grouped.has(r.id))grouped.get(r.id).appearances.push(...appearances);else grouped.set(r.id,{...r,appearances:[...appearances]});}rows=[...grouped.values()];for(const r of rows){r.appearances.sort((a,b)=>b.date.localeCompare(a.date));r.search=normalize([r.title,...r.body,...r.original_titles,...r.sources,...r.topics].join(' '));}rows.sort((a,b)=>b.appearances[0].date.localeCompare(a.appearances[0].date)||a.title.localeCompare(b.title,'ko'));ready=true;options('topic',rows.flatMap(r=>r.topics));options('source',rows.flatMap(r=>r.sources));filter();}catch(e){if(current!==generation)return;rows=[];$('result-count').textContent='불러오기 실패';$('status').textContent='자료를 불러오지 못했습니다. 연결을 확인한 뒤 다시 시도해 주세요. 일부 결과를 전체 결과로 표시하지 않습니다.';$('retry').hidden=false;}}
const initial=new URLSearchParams(location.search);for(const id of ids){const value=initial.get(id);if(value){if((id==='topic'||id==='source')&&!Array.from($(id).options).some(o=>o.value===value))$(id).add(new Option(value,value));$(id).value=value;}}
$('filters').addEventListener('submit',e=>e.preventDefault());let timer;for(const id of ['query','kind','topic','source'])$(id).addEventListener(id==='query'?'input':'change',()=>{clearTimeout(timer);timer=setTimeout(filter,id==='query'?120:0);});for(const id of ['from','to'])$(id).addEventListener('change',()=>{save();load();});$('reset').addEventListener('click',()=>{for(const id of ids)$(id).value='';save();load();});$('more').addEventListener('click',more);$('retry').addEventListener('click',load);load();

// Match the briefing theme preference and shared Hub control.
(() => {
  const button = document.getElementById('theme-toggle');
  function label() {
    const dark = document.documentElement.dataset.theme === 'dark';
    const text = dark ? '라이트 모드' : '다크 모드';
    button.querySelector('.theme-text').textContent = text;
    button.setAttribute('aria-label', text + '로 전환');
    button.setAttribute('aria-pressed', String(dark));
  }
  button.addEventListener('click', () => {
    const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem('research-news-theme', next); } catch (_) {}
    label();
  });
  label();
})();
