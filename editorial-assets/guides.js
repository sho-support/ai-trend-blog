document.querySelectorAll('[data-copy-prompt]').forEach(button=>{
  button.addEventListener('click',async()=>{
    const field=document.getElementById(button.dataset.copyPrompt);
    const status=button.parentElement.querySelector('[role="status"]');
    try{await navigator.clipboard.writeText(field.value);status.textContent='コピーしました';}
    catch{
      field.focus();field.select();
      let copied=false;try{copied=document.execCommand('copy');}catch{}
      status.textContent=copied?'コピーしました':'文章を選択しました。コピーして使えます';
    }
  });
});
