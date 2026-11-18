'use strict';
const token = new URLSearchParams(location.search).get('token');
const box = document.getElementById('cells');
let serial = 0, busy = false;
function append(code='') {
  const id = ++serial, cell = document.createElement('div'); cell.className = 'cell';
  const prompt = document.createElement('div'); prompt.className='prompt';prompt.textContent='In ['+id+']';
  const panel = document.createElement('div');panel.className='panel';
  const edit = document.createElement('textarea');edit.value=code;edit.spellcheck=false;
  const toolbar=document.createElement('div');toolbar.className='controls';
  const run=document.createElement('button');run.textContent='▶ 运行';
  const del=document.createElement('button');del.textContent='删除';
  const status=document.createElement('span');status.className='status';
  const output=document.createElement('div');output.className='output';
  run.onclick=()=>execute(cell);
  del.onclick=()=>cell.remove();
  edit.addEventListener('keydown',e=>{
    if(e.key==='Enter'&&e.shiftKey){
      e.preventDefault();
      execute(cell).then(()=>{
        const next=cell.nextElementSibling;
        (next||append()).querySelector('textarea').focus();
      });
    }
    if(e.key==='Tab'){
      e.preventDefault();
      edit.setRangeText('    ',edit.selectionStart,edit.selectionEnd,'end');
    }
  });
  toolbar.append(run,del,status);
  panel.append(edit,toolbar,output);cell.append(prompt,panel);box.append(cell);return cell;
}
async function execute(cell){
  if(busy)return;
  busy=true;
  const status=cell.querySelector('.status'),output=cell.querySelector('.output');
  status.textContent='运行中…';
  try{
    const response=await fetch('/run',{method:'POST',headers:{'Content-Type':'application/json','X-Notebook-Token':token},body:JSON.stringify({code:cell.querySelector('textarea').value})});
    const result=await response.json();
    if(!response.ok)throw new Error(result.error||'请求失败');
    output.textContent=(result.stdout||'')+(result.stderr||'');
    output.className='output'+(result.ok?'':' bad');
    status.textContent=result.ok?'完成':'错误';
  }catch(error){
    output.textContent=String(error);output.className='output bad';status.textContent='出错';
  }finally{busy=false;}
}
function collect(){return [...box.children].map(cell=>({code:cell.querySelector('textarea').value,output:cell.querySelector('.output').textContent}));}
function save(){
  const blob=new Blob([JSON.stringify({format:'siebla-notebook-v1',cells:collect()},null,2)],{type:'application/json'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='我的笔记本.json';a.click();
  setTimeout(()=>URL.revokeObjectURL(a.href),1000);
}
document.getElementById('add').onclick=()=>append().querySelector('textarea').focus();
document.getElementById('all').onclick=async()=>{for(const cell of [...box.children])await execute(cell);};
document.getElementById('save').onclick=save;
document.getElementById('load').onclick=()=>document.getElementById('file').click();
document.getElementById('file').onchange=async e=>{
  const file=e.target.files[0];if(!file)return;
  try{
    const data=JSON.parse(await file.text());
    let cells;
    if(data.format==='siebla-notebook-v1')cells=data.cells;
    else if(Array.isArray(data.cells))cells=data.cells.filter(x=>x.cell_type==='code').map(x=>Array.isArray(x.source)?x.source.join(''):x.source);
    else throw Error('不支持的格式');
    if(!Array.isArray(cells)||cells.length>1000)throw Error('无效单元格');
    box.replaceChildren();
    for(const entry of cells){const code=typeof entry==='string'?entry:String(entry.code||'');const cell=append(code);if(entry&&typeof entry==='object'){cell.querySelector('.output').textContent=String(entry.output||'');}}
    if(!cells.length)append();
  }catch(error){alert('打开失败：'+error.message);}
  e.target.value='';
};
document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='s'){e.preventDefault();save();}});
append('import sys\nprint("Python", sys.version.split()[0])\nprint("解释器：", sys.executable)');

document.getElementById('dlc').onclick=()=>document.getElementById('dlc-file').click();
document.getElementById('dlc-file').onchange=async e=>{
  const file=e.target.files[0];if(!file)return;
  const button=document.getElementById('dlc');button.disabled=true;
  const old=button.textContent;button.textContent='导入中…';
  try{
    const response=await fetch('/dlc',{method:'POST',
      headers:{'X-Notebook-Token':token,'X-DLC-Name':encodeURIComponent(file.name),
               'Content-Type':'application/zip'},
      body:file});
    const data=await response.json();
    if(!response.ok)throw new Error(data.error||'DLC 导入失败');
    alert(data.message||'DLC 导入成功');
  }catch(error){alert('DLC 导入失败：'+String(error));}
  finally{e.target.value='';button.disabled=false;button.textContent=old;}
};

document.getElementById('dlc-list').onclick=async()=>{
  try{
    const response=await fetch('/dlc-status',{headers:{'X-Notebook-Token':token}});
    const data=await response.json();
    if(!response.ok)throw Error(data.error||'查询失败');
    const items=data.installed||[];
    const lines=items.length?items.map((item,i)=>
      (i+1)+'. '+item.name+'\n   '+item.status):['尚未加载任何 DLC'];
    alert('已加载 DLC\n\n'+lines.join('\n\n'));
  }catch(error){alert('查询 DLC 失败：'+String(error));}
};
