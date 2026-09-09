export async function clickElement(send, evaluate, expression, delay = 150) {
  await evaluate(`(()=>{const el=(${expression});if(!el)throw Error('Element not found');el.scrollIntoView({block:'center',behavior:'instant'});return true})()`);
  let point, previous, stable = 0;
  for (let i = 0; i < 12; i++) {
    await new Promise(resolve => setTimeout(resolve, delay));
    point = await evaluate(`(()=>{const el=(${expression});if(!el)throw Error('Element disappeared');const r=el.getBoundingClientRect(),x=r.x+r.width/2,y=r.y+r.height/2,hit=document.elementFromPoint(x,y);return {x,y,w:r.width,h:r.height,hit:!!hit&&(hit===el||el.contains(hit))}})()`);
    stable = point.hit && point.w > 0 && point.h > 0 && previous &&
      Math.abs(point.x-previous.x)<0.5 && Math.abs(point.y-previous.y)<0.5 ? stable+1 : 0;
    if (stable >= 2) break;
    previous = point;
  }
  if (stable < 2) throw Error('Element obscured or layout did not settle; no click sent');
  await send('Input.dispatchMouseEvent', {type:'mouseMoved',x:point.x,y:point.y});
  await send('Input.dispatchMouseEvent', {type:'mousePressed',x:point.x,y:point.y,button:'left',clickCount:1});
  await send('Input.dispatchMouseEvent', {type:'mouseReleased',x:point.x,y:point.y,button:'left',clickCount:1});
  return point;
}
