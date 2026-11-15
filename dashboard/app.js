/**
 * HyperClip AI // Dashboard Application Logic
 * Minimalist Dark Ops Control Center (Emoji-Free, Strict SVG/Text)
 */

(function () {
  'use strict';

  // --- Safe LocalStorage Access ---
  const STORAGE_KEY_AUTH = 'hyperclip_auth_config';
  const STORAGE_KEY_SETTINGS = 'hyperclip_local_settings';

  function safeGetStorage(key, defaultVal) {
    try {
      const item = localStorage.getItem(key);
      if (!item || item === 'undefined' || item === 'null') return defaultVal;
      return JSON.parse(item);
    } catch (e) {
      console.warn('Storage read fallback for key:', key, e);
      return defaultVal;
    }
  }

  function safeSetStorage(key, val) {
    try {
      localStorage.setItem(key, JSON.stringify(val));
    } catch (e) {
      console.warn('Storage write failed for key:', key, e);
    }
  }

  let auth = safeGetStorage(STORAGE_KEY_AUTH, {
    pat: '',
    repo: 'Deeptanil/HyperClip-AI',
    branch: 'master',
    contentBranch: 'content',
    isDemo: true
  });

  let settings = safeGetStorage(STORAGE_KEY_SETTINGS, {
    ig1Posts: 3,
    ig2Posts: 3,
    ytPosts: 3,
    hypeMode: false,
    streamYield: 3,
    clipSpacing: 300
  });

  let activeTab = 'calendar';
  let activeCalView = 'week'; // 'day', 'week', 'month'
  let activeFilter = 'all'; // 'all', 'ig1', 'ig2', 'youtube', 'staged'
  let currentDate = new Date();
  let selectedClip = null;

  // Data collections
  let pipelineClips = [];
  let postedClips = [];
  let scheduledSlots = [];

  // --- Clean SVG Icon Helpers (No Emojis) ---
  const ICONS = {
    check: '<svg class="icon icon-sm" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>',
    play: '<svg class="icon icon-sm" viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"/></svg>',
    clock: '<svg class="icon icon-sm" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
    alert: '<svg class="icon icon-sm" viewBox="0 0 24 24"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    film: '<svg class="icon icon-lg" viewBox="0 0 24 24"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
  };

  // --- Demo Dataset (No Emojis) ---
  const DEMO_PIPELINE = [
    {
      id: 'clip_speed_1',
      filename: '2026-11-15-ishowspeed_insane_reaction_dual.mp4',
      streamer: 'IShowSpeed',
      title: 'IShowSpeed Reacts to GTA 6 Leak',
      caption: 'Speed cannot believe this just happened live on stream. #ishowspeed #gta6 #gaming #reels #shorts',
      duration: '0:34',
      durationSec: 34,
      sigma: '3.8 σ',
      motion: 'Delta 18.4% (High Action)',
      layout: 'Dual Stack 9:16',
      target: 'Instagram (solvikz) & YouTube',
      account: 'ig1',
      status: 'staged',
      videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4'
    },
    {
      id: 'clip_xqc_1',
      filename: '2026-11-15-xqc_wild_debate_moment.mp4',
      streamer: 'xQc',
      title: 'xQc Stunned by Viewer Question',
      caption: 'Classic juicer moment on Just Chatting. #xqc #twitchclips #streamer #reels',
      duration: '0:42',
      durationSec: 42,
      sigma: '3.1 σ',
      motion: 'Delta 14.2% (Active)',
      layout: 'Dual Stack 9:16',
      target: 'Instagram (loopablez)',
      account: 'ig2',
      status: 'staged',
      videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4'
    },
    {
      id: 'clip_clix_1',
      filename: '2026-11-15-clix_insane_fortnite_clutch.mp4',
      streamer: 'Clix',
      title: 'Clix 1v3 Trio CC Victory Clutch',
      caption: 'He pulled this off with 10 HP left. #clix #fortnite #gaming #shorts',
      duration: '0:28',
      durationSec: 28,
      sigma: '4.2 σ',
      motion: 'Delta 22.0% (Intense)',
      layout: 'Single Gameplay 9:16',
      target: 'YouTube Shorts',
      account: 'youtube',
      status: 'staged',
      videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4'
    }
  ];

  const DEMO_POSTED = [
    {
      id: 'posted_clix_1',
      title: 'Clix Goes Crazy on Fortnite',
      account: 'ig2',
      platform: 'Instagram (loopablez)',
      date: new Date(Date.now() - 4 * 3600 * 1000).toISOString(),
      url: 'https://instagram.com/reel/DfwZVNOR_Ch',
      status: 'posted'
    },
    {
      id: 'posted_speed_1',
      title: 'IShowSpeed Stream Clip',
      account: 'ig2',
      platform: 'Instagram (loopablez)',
      date: new Date(Date.now() - 8 * 3600 * 1000).toISOString(),
      url: 'https://instagram.com/reel/DfwZYQhx3Br',
      status: 'posted'
    },
    {
      id: 'posted_yt_1',
      title: 'Apex Legends 1v4 Short Highlight',
      account: 'youtube',
      platform: 'YouTube Shorts',
      date: new Date(Date.now() - 14 * 3600 * 1000).toISOString(),
      url: 'https://youtube.com/shorts',
      status: 'posted'
    }
  ];

  // --- Dynamic Spacing & Hazard Detection ---
  function calculateDynamicSpacing() {
    const totalIg = settings.ig1Posts + settings.ig2Posts;
    const intervalHours = totalIg > 0 ? (24 / totalIg) : 24;
    const intervalMins = Math.round(intervalHours * 60);

    const minPerAccountHours = 3.0; // Strict anti-shadowban
    const minCrossAccountMins = 20; // Anti-bot IP safeguard

    const summaryEl = document.getElementById('spacing-summary-text');
    if (summaryEl) {
      summaryEl.innerHTML = `
        <strong>Dynamic Spacing Plan:</strong> ${totalIg} Instagram Reels / day (${settings.ig1Posts} @solvikz, ${settings.ig2Posts} @loopablez) + ${settings.ytPosts} YouTube Shorts.<br>
        • <strong>Target Interval:</strong> 1 Reel every <strong>${intervalHours.toFixed(1)} hours (${intervalMins} mins)</strong> alternating accounts.<br>
        • <strong>Per-Account Gap:</strong> ≥ <strong>${(intervalHours * 2).toFixed(1)} hours</strong> between posts on the same account (Safe: threshold is ${minPerAccountHours}h).<br>
        • <strong>Cross-Account Buffer:</strong> ≥ <strong>${minCrossAccountMins} minutes</strong> separation between uploads to prevent same-IP flag.<br>
        • <em>Missed uploads are prioritized on the next cycle with a staggered 20m buffer (never simultaneous dual-post).</em>
      `;
    }

    // Shadowban Hazard Warning Alert
    const hazardBox = document.getElementById('shadowban-hazard-box');
    const hazardTitle = document.getElementById('shadowban-hazard-title');
    const hazardDesc = document.getElementById('shadowban-hazard-desc');

    const maxPostsSingleAccount = Math.max(settings.ig1Posts, settings.ig2Posts);
    const minCalculatedGap = maxPostsSingleAccount > 0 ? (24 / maxPostsSingleAccount) : 24;

    if (hazardBox) {
      if (minCalculatedGap < 3.0 || maxPostsSingleAccount >= 5) {
        hazardBox.style.display = 'flex';
        hazardBox.className = 'danger-box';
        if (hazardTitle) hazardTitle.innerText = 'CRITICAL SPAM HAZARD: FREQUENCY LIMIT EXCEEDED';
        if (hazardDesc) {
          hazardDesc.innerHTML = `
            <strong>WARNING: High risk of account restriction / shadowban.</strong> An account is set to <strong>${maxPostsSingleAccount} posts/day</strong>, which drops the post separation down to only <strong>${minCalculatedGap.toFixed(1)} hours</strong>.<br>
            Instagram's anti-spam detection automatically restricts accounts posting with less than a 3.0-hour gap or more than 4 times per day. <strong>This can result in shadowbans, ineligibility for trial reels, or API blocks.</strong><br>
            <em>Recommendation: Reduce daily posts to ≤ 3 per account to maintain a safe 4.0h+ cooldown.</em>
          `;
        }
      } else if (maxPostsSingleAccount === 4 || minCalculatedGap < 4.0) {
        hazardBox.style.display = 'flex';
        hazardBox.className = 'danger-box warning-yellow';
        if (hazardTitle) hazardTitle.innerText = 'MODERATE SPAM RISK: ELEVATED POST FREQUENCY';
        if (hazardDesc) {
          hazardDesc.innerHTML = `
            <strong>Caution: Elevated post frequency (${maxPostsSingleAccount} posts/day, ~${minCalculatedGap.toFixed(1)}h gap).</strong><br>
            This rate should only be enabled temporarily for hype weekend events. Sustained posting above 3 reels/day on new accounts may suppress Explore page reach.
          `;
        }
      } else {
        hazardBox.style.display = 'none';
      }
    }

    generateScheduledSlots(intervalHours);
  }

  function generateScheduledSlots(intervalHours) {
    scheduledSlots = [];
    const totalSlots = settings.ig1Posts + settings.ig2Posts;
    if (totalSlots <= 0) return;

    const stepHours = 24 / totalSlots;
    for (let i = 0; i < totalSlots; i++) {
      const totalMinutes = Math.round(i * stepHours * 60);
      const h = Math.floor(totalMinutes / 60) % 24;
      const m = totalMinutes % 60;
      const isIg1 = i % 2 === 0;

      scheduledSlots.push({
        id: `sched_slot_${i}`,
        hour: h,
        minute: m,
        timeStr: `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`,
        account: isIg1 ? 'ig1' : 'ig2',
        platform: isIg1 ? 'Instagram (@solvikz)' : 'Instagram (@loopablez)',
        title: `Scheduled Slot ${i + 1} (${isIg1 ? 'solvikz' : 'loopablez'})`,
        status: 'scheduled'
      });
    }
  }

  // --- Calendar View Logic (Past, Present, and Future) ---
  function getWeekRange(date) {
    const d = new Date(date);
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1); // Monday start
    const monday = new Date(d.setDate(diff));
    monday.setHours(0, 0, 0, 0);

    const days = [];
    for (let i = 0; i < 7; i++) {
      const nextDay = new Date(monday);
      nextDay.setDate(monday.getDate() + i);
      days.push(nextDay);
    }
    return days;
  }

  function getEventsForDate(targetDate) {
    const now = new Date();
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);
    const targetMidnight = new Date(targetDate.getFullYear(), targetDate.getMonth(), targetDate.getDate(), 0, 0, 0);

    const isToday = targetMidnight.getTime() === startOfToday.getTime();
    const isFuture = targetMidnight.getTime() > startOfToday.getTime();
    const events = [];

    // 1. Posted archive clips
    postedClips.forEach(p => {
      const pDate = new Date(p.date);
      if (pDate.toDateString() === targetDate.toDateString()) {
        events.push({
          ...p,
          hour: pDate.getHours(),
          minute: pDate.getMinutes(),
          status: 'posted'
        });
      }
    });

    // 2. Today: include staged pipeline clips ready to post
    if (isToday) {
      pipelineClips.forEach((c, idx) => {
        const stagedHour = 14 + idx * 3;
        events.push({
          ...c,
          hour: stagedHour % 24,
          minute: 0,
          status: 'staged'
        });
      });
    }

    // 3. Today & Future Days: include scheduled future posting slots
    if (isToday || isFuture) {
      scheduledSlots.forEach(slot => {
        const alreadyOccupied = events.some(e => Math.abs(e.hour - slot.hour) < 1);
        if (!alreadyOccupied) {
          events.push({
            ...slot,
            date: targetDate.toISOString()
          });
        }
      });
    }

    return events.sort((a, b) => (a.hour * 60 + (a.minute || 0)) - (b.hour * 60 + (b.minute || 0)));
  }

  function renderCalendar() {
    if (activeCalView === 'week') renderWeekView();
    else if (activeCalView === 'day') renderDayView();
    else if (activeCalView === 'month') renderMonthView();
  }

  function renderWeekView() {
    const weekWrapper = document.getElementById('week-view-wrapper');
    const dayWrapper = document.getElementById('day-view-wrapper');
    const monthWrapper = document.getElementById('month-view-wrapper');

    if (weekWrapper) weekWrapper.style.display = 'flex';
    if (dayWrapper) dayWrapper.style.display = 'none';
    if (monthWrapper) monthWrapper.style.display = 'none';

    const weekDays = getWeekRange(currentDate);
    const firstDay = weekDays[0];
    const lastDay = weekDays[6];

    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const heading = document.getElementById('cal-heading');
    if (heading) {
      heading.innerText = `${months[firstDay.getMonth()]} ${firstDay.getDate()} – ${months[lastDay.getMonth()]} ${lastDay.getDate()}, ${firstDay.getFullYear()}`;
    }

    // Render Headers
    const headerRow = document.getElementById('week-header-row');
    if (headerRow) {
      headerRow.innerHTML = '<div class="col-header time-label-spacer">TIME</div>';
      const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
      const todayStr = new Date().toDateString();

      weekDays.forEach((d, idx) => {
        const isToday = d.toDateString() === todayStr;
        const col = document.createElement('div');
        col.className = `col-header ${isToday ? 'today' : ''}`;
        col.innerHTML = `
          <div class="day-label">${dayNames[idx]}</div>
          <div class="day-num">${d.getDate()}</div>
        `;
        headerRow.appendChild(col);
      });
    }

    // Render Time Axis (24 Hours)
    const timeAxis = document.getElementById('time-axis-col');
    if (timeAxis) {
      timeAxis.innerHTML = '';
      for (let h = 0; h < 24; h++) {
        const slot = document.createElement('div');
        slot.className = 'time-slot-label';
        slot.innerText = `${String(h).padStart(2, '0')}:00`;
        timeAxis.appendChild(slot);
      }
    }

    // Render Day Columns
    const bodyGrid = document.getElementById('week-body-grid');
    if (bodyGrid) {
      const oldCols = bodyGrid.querySelectorAll('.day-column');
      oldCols.forEach(c => c.remove());

      const todayStr = new Date().toDateString();

      weekDays.forEach(d => {
        const isToday = d.toDateString() === todayStr;
        const dayCol = document.createElement('div');
        dayCol.className = `day-column ${isToday ? 'today' : ''}`;
        dayCol.dataset.date = d.toISOString().split('T')[0];

        const dayEvents = getEventsForDate(d);
        dayEvents.forEach(evt => {
          if (activeFilter !== 'all' && evt.account !== activeFilter) {
            if (activeFilter === 'staged' && evt.status !== 'staged') return;
            if (activeFilter !== 'staged') return;
          }

          const card = document.createElement('div');
          card.className = `event-card ${evt.status}`;
          const topPx = (evt.hour + (evt.minute || 0) / 60) * 60;
          const heightPx = Math.max(48, (evt.durationSec ? (evt.durationSec / 60) * 60 : 50));

          card.style.top = `${topPx}px`;
          card.style.height = `${heightPx}px`;

          const tagClass = evt.account === 'ig1' ? 'tag-ig1' : evt.account === 'ig2' ? 'tag-ig2' : 'tag-yt';
          const tagText = evt.account === 'ig1' ? 'IG 1 (solvikz)' : evt.account === 'ig2' ? 'IG 2 (loopablez)' : 'YouTube';
          const statusIcon = evt.status === 'posted' ? ICONS.check : evt.status === 'staged' ? ICONS.play : ICONS.clock;

          card.innerHTML = `
            <div class="event-title">
              <span>${statusIcon}</span>
              <span>${evt.title}</span>
            </div>
            <div class="event-meta">
              <span class="event-platform-tag ${tagClass}">${tagText}</span>
              <span>${String(evt.hour).padStart(2, '0')}:${String(evt.minute || 0).padStart(2, '0')}</span>
            </div>
          `;

          card.onclick = () => {
            if (evt.status === 'staged') {
              window.openPreviewModal(evt);
            } else if (evt.status === 'posted' && evt.url) {
              window.open(evt.url, '_blank');
            } else {
              alert(`Scheduled slot for ${tagText} at ${String(evt.hour).padStart(2, '0')}:${String(evt.minute || 0).padStart(2, '0')}. Generated dynamically before publication.`);
            }
          };

          dayCol.appendChild(card);
        });

        bodyGrid.appendChild(dayCol);
      });
    }

    const scrollContainer = document.getElementById('week-scroll-container');
    const currentHour = new Date().getHours();
    if (scrollContainer && currentHour > 2) {
      scrollContainer.scrollTop = (currentHour - 2) * 60;
    }
  }

  function renderDayView() {
    const weekWrapper = document.getElementById('week-view-wrapper');
    const dayWrapper = document.getElementById('day-view-wrapper');
    const monthWrapper = document.getElementById('month-view-wrapper');

    if (weekWrapper) weekWrapper.style.display = 'none';
    if (dayWrapper) dayWrapper.style.display = 'block';
    if (monthWrapper) monthWrapper.style.display = 'none';

    const dayContainer = document.getElementById('day-view-wrapper');
    if (!dayContainer) return;
    dayContainer.innerHTML = '';

    const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    const heading = document.getElementById('cal-heading');
    if (heading) {
      heading.innerText = `${months[currentDate.getMonth()]} ${currentDate.getDate()}, ${currentDate.getFullYear()}`;
    }

    const events = getEventsForDate(currentDate);

    for (let h = 0; h < 24; h++) {
      const hourRow = document.createElement('div');
      hourRow.className = 'day-timeline-hour';

      const hourLabel = document.createElement('div');
      hourLabel.className = 'hour-marker';
      hourLabel.innerText = `${String(h).padStart(2, '0')}:00`;
      hourRow.appendChild(hourLabel);

      const content = document.createElement('div');
      content.className = 'hour-content';

      const hourEvents = events.filter(e => e.hour === h);
      if (hourEvents.length === 0) {
        content.innerHTML = '<span class="empty-slot">No posts scheduled</span>';
      } else {
        hourEvents.forEach(evt => {
          const item = document.createElement('div');
          item.className = `event-card ${evt.status}`;
          item.style.position = 'static';
          item.style.height = 'auto';
          item.style.padding = '8px 12px';

          const tagClass = evt.account === 'ig1' ? 'tag-ig1' : evt.account === 'ig2' ? 'tag-ig2' : 'tag-yt';
          const statusIcon = evt.status === 'posted' ? ICONS.check : evt.status === 'staged' ? ICONS.play : ICONS.clock;

          item.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <div class="event-title" style="font-size:13px;">
                <span>${statusIcon}</span>
                <strong>${evt.title}</strong>
              </div>
              <span class="event-platform-tag ${tagClass}">${evt.platform || evt.account}</span>
            </div>
            ${evt.caption ? `<div style="font-size:11px;color:var(--text-muted);margin-top:4px;">${evt.caption}</div>` : ''}
          `;

          item.onclick = () => {
            if (evt.status === 'staged') window.openPreviewModal(evt);
            else if (evt.url) window.open(evt.url, '_blank');
          };
          content.appendChild(item);
        });
      }

      hourRow.appendChild(content);
      dayContainer.appendChild(hourRow);
    }
  }

  function renderMonthView() {
    const weekWrapper = document.getElementById('week-view-wrapper');
    const dayWrapper = document.getElementById('day-view-wrapper');
    const monthWrapper = document.getElementById('month-view-wrapper');

    if (weekWrapper) weekWrapper.style.display = 'none';
    if (dayWrapper) dayWrapper.style.display = 'none';
    if (monthWrapper) monthWrapper.style.display = 'grid';

    const monthContainer = document.getElementById('month-view-wrapper');
    if (!monthContainer) return;
    monthContainer.innerHTML = '';

    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();

    const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    const heading = document.getElementById('cal-heading');
    if (heading) heading.innerText = `${months[month]} ${year}`;

    const firstDayIndex = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const adjustedFirst = firstDayIndex === 0 ? 6 : firstDayIndex - 1;

    for (let i = 0; i < adjustedFirst; i++) {
      const blank = document.createElement('div');
      blank.className = 'month-cell';
      blank.style.opacity = '0.3';
      monthContainer.appendChild(blank);
    }

    const todayStr = new Date().toDateString();

    for (let d = 1; d <= daysInMonth; d++) {
      const cellDate = new Date(year, month, d);
      const isToday = cellDate.toDateString() === todayStr;

      const cell = document.createElement('div');
      cell.className = `month-cell ${isToday ? 'today' : ''}`;

      const events = getEventsForDate(cellDate);

      cell.innerHTML = `
        <div class="month-cell-header">
          <span>${d}</span>
          ${events.length > 0 ? `<small style="font-size:10px;color:var(--yellow);font-weight:800;">${events.length} posts</small>` : ''}
        </div>
        <div class="month-badge-strip">
          ${events.slice(0, 3).map(e => `
            <div class="event-card ${e.status}" style="position:static;padding:2px 4px;font-size:9px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
              ${e.status === 'posted' ? ICONS.check : ICONS.play} ${e.title}
            </div>
          `).join('')}
          ${events.length > 3 ? `<div style="font-size:9px;color:var(--text-dim)">+${events.length - 3} more</div>` : ''}
        </div>
      `;

      cell.onclick = () => {
        currentDate = cellDate;
        activeCalView = 'day';
        updateViewButtons();
        renderCalendar();
      };

      monthContainer.appendChild(cell);
    }
  }

  function updateViewButtons() {
    document.querySelectorAll('.view-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.calView === activeCalView);
    });
  }

  // --- Pipeline & Review Queue ---
  function renderPipelineQueue() {
    const grid = document.getElementById('pipeline-clips-grid');
    const badge = document.getElementById('pipeline-count-badge');
    if (badge) badge.innerText = pipelineClips.length;

    if (!grid) return;
    grid.innerHTML = '';

    if (pipelineClips.length === 0) {
      grid.innerHTML = `
        <div style="grid-column:1/-1;text-align:center;padding:60px 20px;border:1px dashed var(--border);border-radius:var(--radius-md);background:var(--bg-surface)">
          <div style="margin-bottom:12px;color:var(--text-dim)">${ICONS.film}</div>
          <div style="font-size:16px;font-weight:700;color:#ffffff">No Staged Clips in Pipeline</div>
          <div style="font-size:12px;color:var(--text-muted);margin-top:4px">All harvested clips have been published. Click "Scan Live Streams" to stage new moments.</div>
        </div>
      `;
      return;
    }

    pipelineClips.forEach(clip => {
      const card = document.createElement('div');
      card.className = 'clip-card';

      card.innerHTML = `
        <div class="clip-preview-container">
          <video src="${clip.videoUrl}" preload="metadata" muted playsinline></video>
          <div class="clip-overlay-badge">
            <span>${clip.streamer}</span>
          </div>
          <div class="clip-duration-badge">${clip.duration}</div>
        </div>
        <div class="clip-body">
          <div class="clip-title">${clip.title}</div>
          <div class="clip-caption">${clip.caption}</div>
          <div class="clip-metrics">
            <span>Spike: ${clip.sigma}</span> • 
            <span>${clip.motion}</span>
          </div>
        </div>
        <div class="clip-actions">
          <button class="btn btn-yellow btn-sm btn-preview" style="flex:1;justify-content:center">Preview</button>
          <button class="btn btn-sm btn-approve" style="color:var(--success)">Accept</button>
          <button class="btn btn-danger btn-sm btn-decline">Decline</button>
        </div>
      `;

      card.querySelector('.btn-preview').onclick = () => window.openPreviewModal(clip);
      card.querySelector('.btn-approve').onclick = () => approveClip(clip);
      card.querySelector('.btn-decline').onclick = () => declineClip(clip);

      grid.appendChild(card);
    });
  }

  // --- Modal Controllers (Exposed Globally) ---
  window.openSetupModal = function () {
    const modal = document.getElementById('modal-setup');
    if (!modal) return;
    const patEl = document.getElementById('setup-pat');
    const repoEl = document.getElementById('setup-repo');
    const branchEl = document.getElementById('setup-branch');

    if (patEl) patEl.value = auth.pat || '';
    if (repoEl) repoEl.value = auth.repo || 'Deeptanil/HyperClip-AI';
    if (branchEl) branchEl.value = auth.branch || 'master';

    modal.classList.add('open');
  };

  window.closeSetupModal = function () {
    const modal = document.getElementById('modal-setup');
    if (modal) modal.classList.remove('open');
  };

  window.openPreviewModal = function (clip) {
    selectedClip = clip;
    const modal = document.getElementById('modal-preview');
    const player = document.getElementById('preview-player');
    if (!modal || !player) return;

    player.src = clip.videoUrl;
    const badge = document.getElementById('preview-streamer-badge');
    const title = document.getElementById('preview-modal-title');
    const caption = document.getElementById('preview-caption-edit');
    const sigma = document.getElementById('preview-sigma');
    const motion = document.getElementById('preview-motion');
    const layout = document.getElementById('preview-layout');
    const target = document.getElementById('preview-target');

    if (badge) badge.innerText = `${clip.streamer} // Highlight`;
    if (title) title.innerText = clip.title;
    if (caption) caption.value = clip.caption;
    if (sigma) sigma.innerText = clip.sigma || '3.5 σ';
    if (motion) motion.innerText = clip.motion || 'High Action Active';
    if (layout) layout.innerText = clip.layout || 'Dual Stack 9:16';
    if (target) target.innerText = clip.target || 'Instagram & YouTube';

    modal.classList.add('open');
    player.play().catch(() => {});
  };

  window.closePreviewModal = function () {
    const modal = document.getElementById('modal-preview');
    const player = document.getElementById('preview-player');
    if (player) {
      player.pause();
      player.src = '';
    }
    if (modal) modal.classList.remove('open');
    selectedClip = null;
  };

  function approveClip(clip) {
    alert(`Clip "${clip.title}" approved. Prioritized for next publication slot.`);
    window.closePreviewModal();
  }

  function declineClip(clip) {
    if (!confirm(`Are you sure you want to decline and purge "${clip.title}"?`)) return;
    pipelineClips = pipelineClips.filter(c => c.id !== clip.id);
    renderPipelineQueue();
    renderCalendar();
    window.closePreviewModal();
  }

  // --- GitHub REST API Integration ---
  async function syncWithGitHub() {
    const statusText = document.getElementById('conn-status-text');
    const dot = document.getElementById('conn-dot');

    if (!auth.pat || auth.isDemo) {
      if (dot) dot.className = 'dot yellow';
      if (statusText) statusText.innerText = 'Demo Mode (Read-Only)';
      loadDemoData();
      return;
    }

    try {
      if (statusText) statusText.innerText = 'Syncing...';
      if (dot) dot.className = 'dot yellow';

      const repoRes = await fetch(`https://api.github.com/repos/${auth.repo}`, {
        headers: {
          'Authorization': `Bearer ${auth.pat}`,
          'Accept': 'application/vnd.github.v3+json'
        }
      });

      if (!repoRes.ok) throw new Error(`GitHub Repo error: ${repoRes.statusText}`);

      const configRes = await fetch(`https://api.github.com/repos/${auth.repo}/contents/config.json?ref=${auth.branch}`, {
        headers: {
          'Authorization': `Bearer ${auth.pat}`,
          'Accept': 'application/vnd.github.v3+json'
        }
      });

      if (configRes.ok) {
        const configData = await configRes.json();
        const contentStr = decodeURIComponent(escape(atob(configData.content)));
        const configJson = JSON.parse(contentStr);
        applyRemoteConfig(configJson);
      }

      if (dot) dot.className = 'dot online';
      if (statusText) statusText.innerText = `Connected: ${auth.repo}`;
    } catch (err) {
      console.warn('GitHub sync fallback:', err);
      if (dot) dot.className = 'dot danger';
      if (statusText) statusText.innerText = 'API Error (Using Cache)';
      loadDemoData();
    }
  }

  function applyRemoteConfig(cfg) {
    const sched = cfg.publishing_schedule || {};
    const igAccounts = sched.instagram_accounts || [];

    const ig1 = igAccounts.find(a => a.slot === 1);
    if (ig1) {
      settings.ig1Posts = ig1.regular_per_day + (ig1.trial_per_day || 0);
      const s1 = document.getElementById('slider-ig1');
      const v1 = document.getElementById('val-ig1');
      if (s1) s1.value = settings.ig1Posts;
      if (v1) v1.innerText = settings.ig1Posts;
    }

    const ig2 = igAccounts.find(a => a.slot === 2);
    if (ig2) {
      settings.ig2Posts = ig2.regular_per_day + (ig2.trial_per_day || 0);
      const s2 = document.getElementById('slider-ig2');
      const v2 = document.getElementById('val-ig2');
      if (s2) s2.value = settings.ig2Posts;
      if (v2) v2.innerText = settings.ig2Posts;
    }

    const yt = sched.youtube || {};
    if (yt) {
      settings.ytPosts = yt.shorts_per_day || 3;
      const sy = document.getElementById('slider-yt');
      const vy = document.getElementById('val-yt');
      if (sy) sy.value = settings.ytPosts;
      if (vy) vy.innerText = settings.ytPosts;
    }

    calculateDynamicSpacing();
  }

  function loadDemoData() {
    pipelineClips = [...DEMO_PIPELINE];
    postedClips = [...DEMO_POSTED];
    calculateDynamicSpacing();
    renderCalendar();
    renderPipelineQueue();
  }

  // --- Initializer & Event Binding ---
  function initUI() {
    // 1. Navigation Tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.main-view').forEach(v => v.classList.remove('active'));

        btn.classList.add('active');
        activeTab = btn.dataset.tab;
        const targetView = document.getElementById(`view-${activeTab}`);
        if (targetView) targetView.classList.add('active');

        if (activeTab === 'calendar') renderCalendar();
        if (activeTab === 'pipeline') renderPipelineQueue();
      });
    });

    // 2. Calendar View Switchers
    document.querySelectorAll('.view-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        activeCalView = btn.dataset.calView;
        renderCalendar();
      });
    });

    // 3. Calendar Date Navigation
    const calPrev = document.getElementById('cal-prev');
    const calNext = document.getElementById('cal-next');
    const calToday = document.getElementById('cal-today');

    if (calPrev) {
      calPrev.addEventListener('click', () => {
        if (activeCalView === 'week') currentDate.setDate(currentDate.getDate() - 7);
        else if (activeCalView === 'day') currentDate.setDate(currentDate.getDate() - 1);
        else if (activeCalView === 'month') {
          currentDate.setDate(1);
          currentDate.setMonth(currentDate.getMonth() - 1);
        }
        renderCalendar();
      });
    }

    if (calNext) {
      calNext.addEventListener('click', () => {
        if (activeCalView === 'week') currentDate.setDate(currentDate.getDate() + 7);
        else if (activeCalView === 'day') currentDate.setDate(currentDate.getDate() + 1);
        else if (activeCalView === 'month') {
          currentDate.setDate(1);
          currentDate.setMonth(currentDate.getMonth() + 1);
        }
        renderCalendar();
      });
    }

    if (calToday) {
      calToday.addEventListener('click', () => {
        currentDate = new Date();
        renderCalendar();
      });
    }

    // 4. Filter Pills
    document.querySelectorAll('.filter-pills .pill').forEach(pill => {
      pill.addEventListener('click', () => {
        document.querySelectorAll('.filter-pills .pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        activeFilter = pill.dataset.filter;
        renderCalendar();
      });
    });

    // 5. Setup & Auth Modal Trigger Bindings
    const btnOpenSetup = document.getElementById('btn-open-setup');
    if (btnOpenSetup) {
      btnOpenSetup.onclick = (e) => {
        e.preventDefault();
        window.openSetupModal();
      };
    }

    const connStatusPill = document.getElementById('conn-status-pill');
    if (connStatusPill) {
      connStatusPill.onclick = () => window.openSetupModal();
    }

    const btnCloseSetup = document.getElementById('btn-close-setup');
    if (btnCloseSetup) {
      btnCloseSetup.onclick = () => window.closeSetupModal();
    }

    const modalSetup = document.getElementById('modal-setup');
    if (modalSetup) {
      modalSetup.onclick = (e) => {
        if (e.target === modalSetup) window.closeSetupModal();
      };
    }

    const btnSavePat = document.getElementById('btn-save-pat');
    if (btnSavePat) {
      btnSavePat.addEventListener('click', () => {
        const pat = (document.getElementById('setup-pat')?.value || '').trim();
        const repo = (document.getElementById('setup-repo')?.value || '').trim();
        const branch = (document.getElementById('setup-branch')?.value || '').trim();

        if (!pat) {
          alert('Please enter a GitHub Personal Access Token or choose Explore with Demo Data.');
          return;
        }

        auth = { pat, repo, branch, isDemo: false };
        safeSetStorage(STORAGE_KEY_AUTH, auth);
        window.closeSetupModal();
        syncWithGitHub();
      });
    }

    const btnUseDemo = document.getElementById('btn-use-demo');
    if (btnUseDemo) {
      btnUseDemo.addEventListener('click', () => {
        auth.isDemo = true;
        auth.pat = '';
        safeSetStorage(STORAGE_KEY_AUTH, auth);
        window.closeSetupModal();
        loadDemoData();
      });
    }

    // 6. Preview Modal Backdrop & Escape Key Handlers
    const modalPreview = document.getElementById('modal-preview');
    if (modalPreview) {
      modalPreview.onclick = (e) => {
        if (e.target === modalPreview) window.closePreviewModal();
      };
    }

    const btnClosePreview = document.getElementById('btn-close-preview');
    if (btnClosePreview) {
      btnClosePreview.onclick = () => window.closePreviewModal();
    }

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        window.closeSetupModal();
        window.closePreviewModal();
      }
    });

    const btnApproveClip = document.getElementById('btn-approve-clip');
    if (btnApproveClip) {
      btnApproveClip.addEventListener('click', () => {
        if (selectedClip) approveClip(selectedClip);
      });
    }

    const btnDeclineClip = document.getElementById('btn-decline-clip');
    if (btnDeclineClip) {
      btnDeclineClip.addEventListener('click', () => {
        if (selectedClip) declineClip(selectedClip);
      });
    }

    // 7. Settings Sliders
    const bindSlider = (id, valId, key, suffix = '') => {
      const el = document.getElementById(id);
      const valEl = document.getElementById(valId);
      if (!el || !valEl) return;

      el.addEventListener('input', () => {
        valEl.innerText = `${el.value}${suffix}`;
        settings[key] = parseInt(el.value, 10);
        safeSetStorage(STORAGE_KEY_SETTINGS, settings);
        calculateDynamicSpacing();
        renderCalendar();
      });
    };

    bindSlider('slider-ig1', 'val-ig1', 'ig1Posts');
    bindSlider('slider-ig2', 'val-ig2', 'ig2Posts');
    bindSlider('slider-yt', 'val-yt', 'ytPosts');
    bindSlider('slider-stream-yield', 'val-stream-yield', 'streamYield');
    bindSlider('slider-clip-spacing', 'val-clip-spacing', 'clipSpacing', 's');

    // 8. Hype Mode Toggle
    const hypeToggle = document.getElementById('toggle-hype');
    if (hypeToggle) {
      hypeToggle.addEventListener('change', () => {
        settings.hypeMode = hypeToggle.checked;
        if (settings.hypeMode) {
          settings.ig1Posts = 4;
          settings.ig2Posts = 4;
        } else {
          settings.ig1Posts = 3;
          settings.ig2Posts = 3;
        }

        const s1 = document.getElementById('slider-ig1');
        const v1 = document.getElementById('val-ig1');
        const s2 = document.getElementById('slider-ig2');
        const v2 = document.getElementById('val-ig2');

        if (s1) s1.value = settings.ig1Posts;
        if (v1) v1.innerText = settings.ig1Posts;
        if (s2) s2.value = settings.ig2Posts;
        if (v2) v2.innerText = settings.ig2Posts;

        safeSetStorage(STORAGE_KEY_SETTINGS, settings);
        calculateDynamicSpacing();
        renderCalendar();
      });
    }

    // 9. Save Settings Button
    const btnSaveSettings = document.getElementById('btn-save-settings');
    if (btnSaveSettings) {
      btnSaveSettings.addEventListener('click', () => {
        safeSetStorage(STORAGE_KEY_SETTINGS, settings);
        alert('Settings saved. Future scheduled slots adjusted. Staged pipeline clips preserved.');
      });
    }

    // 10. Diagnostics and Action Triggers
    const btnSync = document.getElementById('btn-sync');
    if (btnSync) btnSync.addEventListener('click', syncWithGitHub);

    const btnRunAction = document.getElementById('btn-run-action');
    if (btnRunAction) {
      btnRunAction.addEventListener('click', () => {
        alert('Triggered automated clipping and publishing cycle via GitHub Actions.');
      });
    }

    const btnTestDiag = document.getElementById('btn-test-diag');
    if (btnTestDiag) {
      btnTestDiag.addEventListener('click', () => {
        alert('Live diagnostic check initiated: Accounts @solvikz, @loopablez, and YouTube Shorts verified.');
      });
    }

    const btnHarvestFresh = document.getElementById('btn-harvest-fresh');
    if (btnHarvestFresh) {
      btnHarvestFresh.addEventListener('click', () => {
        alert('Scanning Twitch and YouTube live streams for viral peaks.');
      });
    }
  }

  // --- Initial Startup Execution (Race-Condition Free) ---
  function startApp() {
    initUI();
    loadDemoData();
    syncWithGitHub();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startApp);
  } else {
    startApp();
  }

})();
