// Menú móvil
function toggleMenu(){document.getElementById('menu').classList.toggle('open');}

// Header con fondo al hacer scroll
(function(){
  var nav=document.querySelector('header.nav');
  if(!nav) return;
  var onScroll=function(){ nav.classList.toggle('scrolled', window.scrollY>20); };
  window.addEventListener('scroll',onScroll,{passive:true}); onScroll();
})();

// Revelado al hacer scroll (respeta reduce-motion)
(function(){
  var els=document.querySelectorAll('.reveal');
  if(!els.length) return;
  if(window.matchMedia('(prefers-reduced-motion:reduce)').matches){
    els.forEach(function(e){e.classList.add('in');}); return;
  }
  var io=new IntersectionObserver(function(ents){
    ents.forEach(function(en){ if(en.isIntersecting){en.target.classList.add('in');io.unobserve(en.target);} });
  },{threshold:.14});
  els.forEach(function(e){io.observe(e);});
})();

// Cookies
(function(){
  if(!window.USE_COOKIES) return;
  if(!localStorage.getItem('mk_cookies')){
    var b=document.getElementById('cookieBanner');
    if(b) b.classList.add('show');
  }
})();
function acceptCookies(v){
  localStorage.setItem('mk_cookies',v);
  var b=document.getElementById('cookieBanner');
  if(b) b.classList.remove('show');
}

// Slots de cita: al cambiar la fecha pide horas libres
function loadSlots(){
  var d=document.getElementById('date'), t=document.getElementById('time');
  if(!d||!t||!d.value) return;
  t.innerHTML='<option>Cargando…</option>';
  fetch('/api/slots?date='+d.value).then(r=>r.json()).then(s=>{
    if(!s.length){t.innerHTML='<option value="">Sin horas libres ese día</option>';return;}
    t.innerHTML=s.map(h=>'<option value="'+h+'">'+h+'</option>').join('');
  });
}
function toggleKind(){
  var k=document.getElementById('kind');
  var m=document.getElementById('maint-fields');
  if(!k||!m) return;
  m.style.display = k.value==='mantenimiento' ? 'block':'none';
}

// Calculadora de financiación (sistema francés)
function calcFin(){
  var P=parseFloat(document.getElementById('amount').value)||0;
  var entr=parseFloat(document.getElementById('down').value)||0;
  var n=parseInt(document.getElementById('months').value)||12;
  var tin=parseFloat(document.getElementById('tin').value)||0;
  document.getElementById('monthsVal').textContent=n;
  var capital=Math.max(P-entr,0);
  var i=tin/100/12;
  var cuota = i>0 ? capital*i/(1-Math.pow(1+i,-n)) : capital/n;
  var total=cuota*n, interes=total-capital;
  document.getElementById('rCuota').textContent=cuota.toFixed(2)+' €';
  document.getElementById('rTotal').textContent=total.toFixed(2)+' €';
  document.getElementById('rInt').textContent=interes.toFixed(2)+' €';
}

// Subida de imágenes en el admin
function uploadImg(input, targetId){
  var fd=new FormData(); fd.append('file', input.files[0]);
  fetch('/admin/upload',{method:'POST',body:fd}).then(r=>r.json()).then(d=>{
    if(d.url){
      var tgt=document.getElementById(targetId);
      tgt.value = tgt.value ? tgt.value+', '+d.url : d.url;
      alert('Imagen subida.');
    } else alert('Error al subir.');
  });
}

/* ===================== CALENDARIO DE CITAS ===================== */
var MK_DOW=['L','M','X','J','V','S','D'];
var MK_MES=['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
function mkPad(n){return String(n).padStart(2,'0');}
function mkEsc(s){var d=document.createElement('div');d.textContent=s==null?'':s;return d.innerHTML;}
function mkFecha(ds){var p=ds.split('-');return p[2]+'/'+p[1]+'/'+p[0];}

function MKAgenda(opts){
  var root=document.getElementById(opts.root); if(!root) return null;
  var today=new Date();
  var start=opts.initDate?new Date(opts.initDate+'T00:00:00'):today;
  var cur=new Date(start.getFullYear(),start.getMonth(),1);
  var selDate=opts.initDate||null;
  root.innerHTML='<div class="cal"><div class="cal-head"><button class="cal-nav" data-d="-1">‹</button>'+
    '<span class="m"></span><button class="cal-nav" data-d="1">›</button></div>'+
    '<div class="cal-grid dows"></div><div class="cal-grid days"></div><div class="cal-legend"></div></div>';
  var mEl=root.querySelector('.m'),dowsEl=root.querySelector('.dows'),daysEl=root.querySelector('.days'),legEl=root.querySelector('.cal-legend');
  MK_DOW.forEach(function(d){var s=document.createElement('div');s.className='cal-dow';s.textContent=d;dowsEl.appendChild(s);});
  legEl.innerHTML='<span><i style="background:#2bd07a"></i>Alta</span><span><i style="background:#f5c542"></i>Media</span>'+
    '<span><i style="background:#ff4326"></i>Sin huecos</span>'+(opts.admin?'<span><i style="background:#c084fc;border-radius:2px"></i>Con bloqueos</span>':'');
  root.querySelectorAll('.cal-nav').forEach(function(b){b.onclick=function(){cur.setMonth(cur.getMonth()+parseInt(b.dataset.d));load();};});

  function load(){
    var y=cur.getFullYear(),m=cur.getMonth()+1;
    mEl.textContent=MK_MES[m-1]+' '+y;
    daysEl.innerHTML='<div style="grid-column:1/-1;text-align:center;color:#6f7d90;font-family:monospace;padding:16px">Cargando…</div>';
    fetch(opts.availUrl+'?year='+y+'&month='+m).then(function(r){return r.json();}).then(function(res){
      daysEl.innerHTML='';
      var offset=(new Date(y,m-1,1).getDay()+6)%7;
      for(var i=0;i<offset;i++){var e=document.createElement('div');e.className='cal-day empty';daysEl.appendChild(e);}
      Object.keys(res.days).forEach(function(d){
        var info=res.days[d],lvl=info.level;
        var cell=document.createElement('div');cell.className='cal-day lvl-'+lvl;
        var ds=y+'-'+mkPad(m)+'-'+mkPad(d);
        cell.innerHTML='<span>'+d+'</span>'+(['high','low','none'].indexOf(lvl)>=0?'<span class="dot"></span>':'');
        if(opts.admin&&info.blocked){cell.innerHTML+='<span class="badge-blk" title="Con bloqueos"></span>';}
        if(['high','low','none'].indexOf(lvl)>=0){
          cell.onclick=function(){
            selDate=ds;
            daysEl.querySelectorAll('.cal-day').forEach(function(c){c.classList.remove('sel');});
            cell.classList.add('sel'); opts.onDay(ds);
          };
          if(selDate===ds){cell.classList.add('sel');}
        }
        daysEl.appendChild(cell);
      });
      if(opts.initDate&&!MKAgenda._init){var sd=opts.initDate.split('-');
        if(parseInt(sd[0])===y&&parseInt(sd[1])===m){MKAgenda._init=true;opts.onDay(opts.initDate);}}
    });
  }
  load();
  return {reload:load};
}

/* ---- Frontend: página de cita ---- */
function initCita(){
  var root=document.getElementById('calRoot'); if(!root) return;
  MKAgenda({root:'calRoot',admin:false,availUrl:'/api/availability',onDay:function(ds){
    var box=document.getElementById('slotBox'); box.innerHTML='<div class="day-empty">Cargando…</div>';
    document.getElementById('f_date').value=ds; document.getElementById('f_time').value='';
    var lbl=document.getElementById('selSlot'); if(lbl)lbl.textContent='—';
    fetch('/api/slots?date='+ds).then(function(r){return r.json();}).then(function(res){
      if(!res.slots.length){box.innerHTML='<div class="day-empty">Ese día no abrimos para citas online. Prueba otro día o pide una cita de consulta.</div>';return;}
      box.innerHTML='<p style="font-family:var(--mono);font-size:.8rem;color:var(--ink-3);text-transform:uppercase;letter-spacing:.1em;margin:0 0 12px">Franjas · '+mkFecha(ds)+'</p><div class="slots"></div>';
      var g=box.querySelector('.slots');
      res.slots.forEach(function(s){
        var el=document.createElement(s.available?'button':'span');
        if(s.available)el.type='button';
        el.className='slot '+(s.available?'free':'unavail'); el.textContent=s.t;
        if(s.available){el.onclick=function(){
          g.querySelectorAll('.slot').forEach(function(x){x.classList.remove('sel');});
          el.classList.add('sel');
          document.getElementById('f_time').value=s.t;
          var lbl=document.getElementById('selSlot'); if(lbl)lbl.textContent=mkFecha(ds)+' · '+s.t;
        };}
        g.appendChild(el);
      });
    });
  }});
}

/* ---- Backoffice: agenda ---- */
function initAgendaAdmin(){
  var root=document.getElementById('calAdmin'); if(!root) return;
  var init=new URLSearchParams(location.search).get('d')||null;
  MKAgenda({root:'calAdmin',admin:true,availUrl:'/admin/api/availability',initDate:init,onDay:loadAdminDay});

  function loadAdminDay(ds){
    var panel=document.getElementById('dayPanel');
    panel.innerHTML='<div class="day-empty">Cargando…</div>';
    fetch('/admin/api/day?date='+ds).then(function(r){return r.json();}).then(function(res){
      renderDay(ds,res);
    });
  }
  function backField(ds){return '<input type="hidden" name="back" value="/admin/agenda?d='+ds+'">';}

  function renderDay(ds,res){
    var panel=document.getElementById('dayPanel');
    if(!res.slots.length){panel.innerHTML='<h3>'+mkFecha(ds)+'</h3><div class="day-empty">Sin horario de citas configurado para este día.</div>';return;}
    var html='<div style="display:flex;justify-content:space-between;align-items:center">'+
      '<h3 style="margin:0">'+mkFecha(ds)+'</h3>'+
      '<button class="btn ghost sm no-print" onclick="window.print()">Imprimir resumen</button></div>';
    // franjas
    html+='<div class="slots" style="margin:16px 0 8px">';
    res.slots.forEach(function(s,i){
      var cls=s.status==='free'?'free':(s.status==='booked'?'booked':(s.status==='blocked'?'blocked':'past'));
      var mk=s.status==='booked'?'•':(s.status==='blocked'?'🔒':'');
      html+='<button type="button" class="slot '+cls+'" onclick="window.__agSel('+i+')">'+s.t+
            (mk?'<span class="mk">'+mk+'</span>':'')+'</button>';
    });
    html+='</div><div id="slotDetail"></div>';
    // resumen imprimible
    html+='<div class="print-area" style="margin-top:24px"><h3 style="font-size:1.1rem">Resumen del día · '+mkFecha(ds)+'</h3>';
    if(!res.summary.length){html+='<p class="muted">Sin citas ni bloqueos.</p>';}
    else{
      html+='<table class="summary-table"><tr><th>Hora</th><th>Cliente / Motivo</th><th>Contacto</th><th>Estado</th><th class="no-print">Acciones</th></tr>';
      res.summary.forEach(function(s){
        if(s.status==='booked'){
          html+='<tr><td class="h">'+s.t+'</td><td>'+mkEsc(s.name)+(s.subject?' <span class="muted">· '+mkEsc(s.subject)+'</span>':'')+
            '</td><td class="muted">'+mkEsc(s.phone||'')+'</td><td><span class="chip '+s.estado+'">'+s.estado+'</span></td>'+
            '<td class="no-print"><form method="post" action="/admin/appointments/'+s.id+'" style="display:inline" onsubmit="return confirm(\'¿Anular la cita?\')">'+
            backField(ds)+'<input type="hidden" name="action" value="status"><input type="hidden" name="status" value="cancelada">'+
            '<button class="btn sm danger">Anular</button></form></td></tr>';
        }else{
          html+='<tr><td class="h">'+s.t+'</td><td>🔒 Bloqueado'+(s.reason?': '+mkEsc(s.reason):'')+'</td><td>—</td><td>—</td>'+
            '<td class="no-print"><form method="post" action="/admin/agenda/unblock" style="display:inline">'+
            '<input type="hidden" name="block_id" value="'+s.block_id+'"><input type="hidden" name="date" value="'+ds+'">'+
            '<button class="btn sm ghost">Desbloquear</button></form></td></tr>';
        }
      });
      html+='</table>';
    }
    html+='</div>';
    panel.innerHTML=html;

    // detalle al pinchar franja
    window.__agSel=function(i){
      var s=res.slots[i]; var det=document.getElementById('slotDetail');
      panel.querySelectorAll('.slots .slot').forEach(function(x,j){x.classList.toggle('sel',j===i);});
      if(s.status==='booked'){
        det.innerHTML='<div class="panel" style="margin-top:10px"><h4 style="margin-top:0">'+s.t+' · '+mkEsc(s.name)+
          ' <span class="chip '+s.estado+'">'+s.estado+'</span></h4>'+
          '<p class="muted" style="margin:0 0 12px">Nº '+s.code+' · '+mkEsc(s.phone||'')+' · '+mkEsc(s.email||'')+(s.subject?'<br>Asunto: '+mkEsc(s.subject):'')+'</p>'+
          '<div style="display:flex;gap:10px;flex-wrap:wrap">'+
          '<form method="post" action="/admin/appointments/'+s.id+'" style="display:flex;gap:6px">'+backField(ds)+
          '<input type="hidden" name="action" value="status"><select name="status">'+
          ['pendiente','confirmada','completada','cancelada'].map(function(o){return '<option '+(o===s.estado?'selected':'')+'>'+o+'</option>';}).join('')+
          '</select><button class="btn sm primary">Estado</button></form>'+
          (s.estado!=='completada'?'<form method="post" action="/admin/appointments/'+s.id+'">'+backField(ds)+
          '<input type="hidden" name="action" value="complete"><button class="btn sm ghost" title="Avisa al cliente de que su moto está lista">✓ Moto lista</button></form>':'')+
          '<form method="post" action="/admin/appointments/'+s.id+'" style="display:flex;gap:6px">'+backField(ds)+
          '<input type="hidden" name="action" value="slot"><input type="datetime-local" name="slot" value="'+ds+'T'+s.t+'">'+
          '<button class="btn sm ghost">Reprogramar</button></form>'+
          '<form method="post" action="/admin/appointments/'+s.id+'" onsubmit="return confirm(\'¿Eliminar cita?\')">'+backField(ds)+
          '<input type="hidden" name="action" value="delete"><button class="btn sm danger">Eliminar</button></form>'+
          '</div></div>';
      }else if(s.status==='blocked'){
        det.innerHTML='<div class="panel" style="margin-top:10px"><h4 style="margin-top:0">'+s.t+' · 🔒 Bloqueado</h4>'+
          '<p class="muted">Motivo: '+mkEsc(s.reason||'(sin especificar)')+'</p>'+
          '<form method="post" action="/admin/agenda/unblock"><input type="hidden" name="block_id" value="'+s.block_id+'">'+
          '<input type="hidden" name="date" value="'+ds+'"><button class="btn sm ghost">Desbloquear franja</button></form></div>';
      }else if(s.status==='free'){
        det.innerHTML='<div class="grid g2" style="margin-top:10px;gap:14px">'+
          '<form method="post" action="/admin/agenda/add" class="panel"><h4 style="margin-top:0">Añadir cita · '+s.t+'</h4>'+
          '<input type="hidden" name="date" value="'+ds+'"><input type="hidden" name="time" value="'+s.t+'">'+
          '<div class="field"><label>Cliente</label><input name="name" required></div>'+
          '<div class="row2"><div class="field"><label>Teléfono</label><input name="phone"></div>'+
          '<div class="field"><label>Email</label><input name="email" type="email"></div></div>'+
          '<div class="field"><label>Asunto</label><input name="subject"></div>'+
          '<button class="btn primary wide">Crear cita</button></form>'+
          '<form method="post" action="/admin/agenda/block" class="panel"><h4 style="margin-top:0">Bloquear · '+s.t+'</h4>'+
          '<input type="hidden" name="date" value="'+ds+'"><input type="hidden" name="time" value="'+s.t+'">'+
          '<div class="field"><label>Motivo</label><input name="reason" placeholder="Ej: comida, recogida pieza…"></div>'+
          '<button class="btn ghost wide">Bloquear franja</button></form></div>';
      }else{det.innerHTML='<div class="day-empty">Franja pasada.</div>';}
      det.scrollIntoView({behavior:'smooth',block:'nearest'});
    };
  }
}

document.addEventListener('DOMContentLoaded',function(){initCita();initAgendaAdmin();});
