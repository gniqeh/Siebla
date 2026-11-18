'use strict';
const token = new URLSearchParams(location.search).get('token');
const cellsBox = document.getElementById('cells');
const saveState = document.getElementById('save-state');
const runState = document.getElementById('run-state');
const infoDialog = document.getElementById('info-dialog');
let busy = false;
let dirty = false;
let serial = 0;
let autoTimer = null;
let saving = Promise.resolve();
let selectedCell = null, commandMode = false, deleteArmedUntil = 0;
let completionSequence = 0, completionTimer = null, completionMenu = null;
let completionItems = [], completionIndex = 0, completionEditor = null, completionPartial = '';
let composing = false;

async function api(path, options={}) {
  const response = await fetch(path, {
    ...options,
    headers: {'X-Notebook-Token':token, ...(options.headers||{})}
  });
  const result = await response.json();
  if (!response.ok) throw Error(result.error || '操作失败');
  return result;
}

function updateNumbers() {
  [...cellsBox.children].forEach((cell,i) => {
    cell.querySelector('.prompt').textContent='In ['+(i+1)+']';
  });
}

function markDirty() {
  dirty = true;
  saveState.textContent = '尚未保存的修改';
  saveState.className = 'dirty';
  clearTimeout(autoTimer);
  autoTimer = setTimeout(() => saveLocal(true), 900);
}

function selectCell(cell, command=false) {
  if(selectedCell)selectedCell.classList.remove('selected');
  selectedCell=cell;
  commandMode=command;
  if(cell)cell.classList.add('selected');
  deleteArmedUntil=0;
}
function commandFocus(cell){
  closeCompletion();
  if(document.activeElement && document.activeElement.blur)document.activeElement.blur();
  selectCell(cell,true);
  cell.focus({preventScroll:true});
}
function insertNear(above){
  const target=selectedCell || cellsBox.lastElementChild;
  const cell=append();
  if(target){
    cellsBox.insertBefore(cell,above?target:target.nextSibling);
  }
  updateNumbers();markDirty();commandFocus(cell);
  cell.scrollIntoView({block:'nearest'});
}
function removeSelected(){
  const cell=selectedCell;
  if(!cell)return;
  const target=cell.nextElementSibling || cell.previousElementSibling;
  cell.remove();
  selectedCell=null;
  if(!cellsBox.children.length)append();
  updateNumbers();markDirty();
  commandFocus(target || cellsBox.firstElementChild);
}
function closeCompletion(){
  completionSequence++;
  clearTimeout(completionTimer);completionTimer=null;
  if(completionMenu)completionMenu.remove();
  completionMenu=null;completionItems=[];completionEditor=null;completionPartial='';
}
function caretPrefix(editor){
  if(editor.selectionStart!==editor.selectionEnd)return null;
  const head=editor.value.slice(0,editor.selectionStart);
  const match=head.match(/([A-Za-z_][A-Za-z0-9_.]*)$/);
  if(!match)return null;
  const prefix=match[1];
  if(!/^(?:[A-Za-z_][A-Za-z0-9_]*\.)*[A-Za-z_][A-Za-z0-9_]*$/.test(prefix)
     && !/^(?:[A-Za-z_][A-Za-z0-9_]*\.)+$/.test(prefix))return null;
  return prefix;
}
function acceptCompletion(){
  if(!completionMenu || !completionEditor || !completionItems.length)return false;
  const editor=completionEditor;
  const end=editor.selectionStart;
  editor.setRangeText(completionItems[completionIndex],end-completionPartial.length,end,'end');
  editor.focus();
  closeCompletion();
  editor.dispatchEvent(new Event('input',{bubbles:true}));
  return true;
}
function moveCompletion(amount){
  if(!completionMenu)return;
  completionIndex=(completionIndex+amount+completionItems.length)%completionItems.length;
  [...completionMenu.children].forEach((item,i)=>{
    item.classList.toggle('active',i===completionIndex);
    item.setAttribute('aria-selected',String(i===completionIndex));
  });
  completionMenu.children[completionIndex].scrollIntoView({block:'nearest'});
}
function renderCompletion(editor,items,prefix){
  closeCompletion();
  if(!items.length)return;
  completionEditor=editor;
  completionPartial=prefix.slice(prefix.lastIndexOf('.')+1);
  completionItems=items.slice(0,40);
  completionIndex=0;
  const menu=document.createElement('div');
  menu.className='completion-menu';
  menu.setAttribute('role','listbox');
  for(let i=0;i<completionItems.length;i++){
    const option=document.createElement('div');
    option.className='completion-item'+(i===0?' active':'');
    option.textContent=completionItems[i];
    option.setAttribute('role','option');
    option.setAttribute('aria-selected',String(i===0));
    option.addEventListener('mousedown',event=>{
      event.preventDefault();completionIndex=i;acceptCompletion();
    });
    menu.append(option);
  }
  editor.closest('.panel').append(menu);
  completionMenu=menu;
}
function requestCompletion(editor,immediate=false){
  if(composing || busy)return;
  const prefix=caretPrefix(editor);
  closeCompletion();
  if(!prefix || prefix.length>180)return;
  const requestId=completionSequence;
  completionTimer=setTimeout(async()=>{
    try{
      const data=await api('/complete',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({prefix})
      });
      if(completionSequence!==requestId || document.activeElement!==editor
         || caretPrefix(editor)!==prefix)return;
      const items=(data.items||[]).filter(name=>name!==prefix);
      renderCompletion(editor,items,prefix);
    }catch(error){/* Autocomplete must never block typing. */}
  },immediate?0:160);
}

function append(code='', output='', focus=false) {
  const cell = document.createElement('section');
  cell.className = 'cell';
  cell.tabIndex = 0;
  cell.dataset.id = String(++serial);
  const prompt = document.createElement('div');
  prompt.className = 'prompt';
  const panel = document.createElement('div');
  panel.className = 'panel';
  const editor = document.createElement('textarea');
  editor.className='editor';
  editor.wrap = 'off';
  editor.value=code;
  editor.spellcheck=false;
  editor.setAttribute('aria-label','Python 代码');
  const codeArea = document.createElement('div');
  codeArea.className = 'editor-area';
  const lineNumbers = document.createElement('div');
  lineNumbers.className = 'line-numbers';
  lineNumbers.setAttribute('aria-hidden', 'true');
  const updateLines = () => {
    const count = editor.value.split('\n').length;
    lineNumbers.textContent = Array.from({length:count}, (_,i)=>i+1).join('\n');
  };
  updateLines();
  editor.addEventListener('scroll', () => {
    lineNumbers.scrollTop = editor.scrollTop;
  });
  codeArea.append(lineNumbers, editor);

  const controls = document.createElement('div');
  controls.className='controls';
  const status=document.createElement('span');
  status.className='cell-status';
  const spacer=document.createElement('span');
  spacer.className='spacer';
  const outputBox=document.createElement('div');
  outputBox.className='output';
  outputBox.textContent=output;
  function action(label, callback, className='') {
    const button=document.createElement('button');
    button.textContent=label;
    if(className)button.className=className;
    button.onclick=callback;
    return button;
  }
  const run=action('▶ 运行',()=>execute(cell));
  const up=action('↑ 上移',()=>{
    const previous=cell.previousElementSibling;
    if(previous){cellsBox.insertBefore(cell,previous);updateNumbers();markDirty();}
  });
  const down=action('↓ 下移',()=>{
    const next=cell.nextElementSibling;
    if(next){cellsBox.insertBefore(next,cell);updateNumbers();markDirty();}
  });
  const clear=action('清空输出',()=>{
    outputBox.textContent='';outputBox.className='output';status.textContent='';markDirty();
  });
  const del=action('删除',()=>{
    if(cellsBox.children.length===1 && (editor.value.trim() || outputBox.textContent.trim())) {
      if(!confirm('删除最后一个单元格？'))return;
    }
    cell.remove();
    if(!cellsBox.children.length)append('', '', true);
    updateNumbers();markDirty();
  },'danger');
  controls.append(run,up,down,clear,spacer,status,del);
  editor.addEventListener('input',markDirty);
  editor.addEventListener('keydown',event=>{
    if(event.key==='Enter' && event.shiftKey){
      event.preventDefault();
      execute(cell).then(()=>{
        const next=cell.nextElementSibling || append('','');
        next.querySelector('textarea').focus();
      });
    }else if(event.key==='Tab'){
      event.preventDefault();
      editor.setRangeText('    ',editor.selectionStart,editor.selectionEnd,'end');
      markDirty();
    }
  });
  panel.append(codeArea,controls,outputBox);
  cell.append(prompt,panel);
  cellsBox.append(cell);
  updateNumbers();
  if(focus)editor.focus();
  return cell;
}

function collect(){
  return [...cellsBox.children].map(cell=>({
    code:cell.querySelector('.editor').value,
    output:cell.querySelector('.output').textContent
  }));
}

async function saveLocal(auto=false){
  clearTimeout(autoTimer);
  if(busy && auto) {
    autoTimer=setTimeout(()=>saveLocal(true),900);
    return;
  }
  const snapshot=JSON.stringify({format:'siebla-notebook-v1',cells:collect()});
  const previous=saving;
  saving=previous.catch(()=>{}).then(async()=>{
    const result=await api('/book',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:snapshot
    });
    return result;
  });
  try{
    await saving;
    const current=JSON.stringify({format:'siebla-notebook-v1',cells:collect()});
    if(current===snapshot){
      dirty=false;saveState.textContent='已保存到本地 work 文件夹';saveState.className='ok';
    }else{
      dirty=true;
      markDirty();
    }
  }catch(error){
    dirty=true;saveState.textContent='保存失败：'+error.message;saveState.className='error';
    if(!auto)showInfo('保存失败',error.message);
  }
}

async function execute(cell){
  if(busy)return false;
  busy=true;
  const status=cell.querySelector('.cell-status');
  const output=cell.querySelector('.output');
  status.textContent='运行中…';
  runState.textContent='正在运行，请勿重复点击';
  const all=document.querySelectorAll('.controls button,#all');
  all.forEach(button=>button.disabled=true);
  try {
    const result=await api('/run',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({code:cell.querySelector('.editor').value})
    });
    output.textContent=(result.stdout||'')+(result.stderr||'');
    output.className='output'+(result.ok?'':' bad');
    status.textContent=result.ok?'成功':'出错';
    markDirty();
    return result.ok;
  } catch(error){
    output.textContent=error.message;output.className='output bad';
    status.textContent='失败';
    markDirty();
    return false;
  } finally {
    busy=false;
    all.forEach(button=>button.disabled=false);
    runState.textContent='Shift+Enter 运行当前格 · Ctrl+S 保存';
  }
}

async function runAll(){
  if(busy)return;
  const all=[...cellsBox.children];
  const button=document.getElementById('all');
  button.disabled=true;
  try{
    for(let i=0;i<all.length;i++){
      runState.textContent='运行全部 '+(i+1)+' / '+all.length;
      const success=await execute(all[i]);
      if(!success){
        runState.textContent='第 '+(i+1)+' 个单元格执行失败，已停止';
        await saveLocal();
        return;
      }
    }
    runState.textContent='全部运行完成';
    await saveLocal();
  }finally{button.disabled=false;}
}

function exportBook(){
  const blob=new Blob([JSON.stringify({
    format:'siebla-notebook-v1',cells:collect()
  },null,2)],{type:'application/json'});
  const url=URL.createObjectURL(blob);
  const link=document.createElement('a');
  link.href=url;link.download='Siebla-notebook.json';link.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}

function showInfo(title,text){
  document.getElementById('info-title').textContent=title;
  document.getElementById('info-content').textContent=text;
  infoDialog.showModal();
}

document.getElementById('info-close').onclick=()=>infoDialog.close();
document.getElementById('info-copy').onclick=async()=>{
  const content=document.getElementById('info-content').textContent;
  const button=document.getElementById('info-copy');
  try{
    await navigator.clipboard.writeText(content);
    button.textContent='已复制';
    setTimeout(()=>button.textContent='复制全部',1300);
  }catch(error){
    const selection=window.getSelection();
    const range=document.createRange();
    range.selectNodeContents(document.getElementById('info-content'));
    selection.removeAllRanges();selection.addRange(range);
    button.textContent='已选中，请按 Ctrl+C';
  }
};
document.getElementById('add').onclick=()=>{append('', '', true);markDirty();};
document.getElementById('add-bottom').onclick=()=>{append('', '', true);markDirty();};
document.getElementById('all').onclick=runAll;
document.getElementById('save').onclick=()=>saveLocal();
document.getElementById('export').onclick=exportBook;
document.getElementById('load').onclick=()=>document.getElementById('file').click();
document.getElementById('file').onchange=async event=>{
  const file=event.target.files[0];
  if(!file)return;
  try{
    const data=JSON.parse(await file.text());
    let entries;
    if(data.format==='siebla-notebook-v1' && Array.isArray(data.cells))entries=data.cells;
    else if(Array.isArray(data.cells))entries=data.cells.filter(c=>c.cell_type==='code').map(c=>({
      code:Array.isArray(c.source)?c.source.join(''):String(c.source||''),
      output:''
    }));
    else throw Error('不支持的文件格式');
    if(entries.length>1000)throw Error('单元格数量过多');
    if(dirty && !confirm('导入文件会替换当前笔记本，是否继续？'))return;
    cellsBox.replaceChildren();
    for(const entry of entries)append(String(entry.code||''),String(entry.output||''));
    if(!entries.length)append();
    markDirty();await saveLocal();
  }catch(error){showInfo('导入失败',error.message);}
  finally{event.target.value='';}
};
document.addEventListener('keydown',event=>{
  if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='s'){
    event.preventDefault();saveLocal();
  }
});
window.addEventListener('beforeunload',event=>{
  if(dirty){event.preventDefault();event.returnValue='';}
});

document.getElementById('dlc').onclick=async()=>{
  const button=document.getElementById('dlc');
  button.disabled=true;button.textContent='选择 DLC…';
  try{
    const data=await api('/dlc-select',{
      method:'POST',headers:{'Content-Type':'application/json'},body:'{}'
    });
    if(!data.cancelled)showInfo('DLC 导入结果',data.message||'导入完成');
  }catch(error){showInfo('DLC 导入失败',error.message);}
  finally{button.disabled=false;button.textContent='加载 DLC';}
};
document.getElementById('dlc-list').onclick=async()=>{
  try{
    const data=await api('/dlc-status');
    const items=data.installed||[];
    showInfo('目前加载的 DLC',items.length?items.map(x=>
      x.name+'（'+x.status+'）'+(x.status==='正常'?'':'\n'+(x.detail||''))
    ).join('\n\n'):'尚未加载任何 DLC');
  }catch(error){showInfo('查询失败',error.message);}
};
document.getElementById('ai-capabilities').onclick=async()=>{
  try{
    const data=await api('/capabilities');
    showInfo('当前 Python 环境',data.text);
  }catch(error){showInfo('读取环境失败',error.message);}
};

async function initialize(){
  try{
    const data=await api('/book');
    for(const entry of (data.cells||[])){
      append(String(entry.code||''),String(entry.output||''));
    }
    if(!cellsBox.children.length)append('import sys\nprint("Python", sys.version.split()[0])');
    saveState.textContent=data.saved?'已从本地恢复笔记本':'新笔记本 · 自动保存已开启';
    saveState.className='ok';
  }catch(error){
    append('import sys\nprint(sys.version)');
    saveState.textContent='恢复失败：'+error.message;
    saveState.className='error';
    showInfo('本地笔记本恢复失败',error.message);
  }
}
initialize();
