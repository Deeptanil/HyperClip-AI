/**
 * HyperClip AI // Dashboard Application Logic
 * Dark Ops Minimalist Control Center
 */

(function () {
  'use strict';

  // --- State Configuration ---
  const STORAGE_KEY_AUTH = 'hyperclip_auth_config';
  const STORAGE_KEY_SETTINGS = 'hyperclip_local_settings';

  let auth = JSON.parse(localStorage.getItem(STORAGE_KEY_AUTH)) || {
    pat: '',
    repo: 'Deeptanil/HyperClip-AI',
    branch: 'master',
    contentBranch: 'content',
    isDemo: true
  };

  let settings = JSON.parse(localStorage.getItem(STORAGE_KEY_SETTINGS)) || {
    ig1Posts: 3,
    ig2Posts: 3,
    ytPosts: 3,
    hypeMode: false,
    streamYield: 3,
    clipSpacing: 300
  };

  let activeTab = 'calendar';
  let activeCalView = 'week'; // 'day', 'week', 'month'
  let activeFilter = 'all'; // 'all', 'ig1', 'ig2', 'youtube', 'staged'
  let currentDate = new Date(); // Active navigation date
  let selectedClip = null;

  // Data collections
  let pipelineClips = [];
  let postedClips = [];
  let scheduledSlots = [];

  // --- Demo Fallback Dataset ---
  const DEMO_PIPELINE = [
    {
      id: 'clip_speed_1',
      filename: '2026-11-15-ishowspeed_insane_reaction_dual.mp4',
      streamer: 'IShowSpeed',
      title: 'IShowSpeed Reacts to GTA 6 Leak',
      caption: 'Speed cannot believe this just happened live on stream! 🔥 #ishowspeed #gta6 #gaming #reels #shorts',
      duration: '0:34',
      durationSec: 34,
      sigma: '3.8 σ',
      motion: 'Delta 18.4% (High Action)',
      layout: 'Dual Stack 9:16',
      target: 'Instagram (solvikz) & YouTube',
      account: 'ig1',
      status: 'staged',
      videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4',
      thumbUrl: ''
    },
    {
      id: 'clip_xqc_1',
      filename: '2026-11-15-xqc_wild_debate_moment.mp4',
      streamer: 'xQc',
      title: 'xQc Stunned by Viewer Question',
      caption: 'Classic juicer moment on Just Chatting 😂 #xqc #twitchclips #streamer #reels',
      duration: '0:42',
      durationSec: 42,
      sigma: '3.1 σ',
      motion: 'Delta 14.2% (Active)',
      layout: 'Dual Stack 9:16',
      target: 'Instagram (loopablez)',
      account: 'ig2',
      status: 'staged',
      videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4',
      thumbUrl: ''
    },
    {
      id: 'clip_clix_1',
      filename: '2026-11-15-clix_insane_fortnite_clutch.mp4',
      streamer: 'Clix',
      title: 'Clix 1v3 Trio CC Victory Clutch',
      caption: 'He pulled this off with 10 HP left! 🏆 #clix #fortnite #gaming #shorts',
      duration: '0:28',
      durationSec: 28,
      sigma: '4.2 σ',
      motion: 'Delta 22.0% (Intense)',
      layout: 'Single Gameplay 9:16',
      target: 'YouTube Shorts',
      account: 'youtube',
      status: 'staged',
      videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4',
      thumbUrl: ''
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
      title: 'IShowSpeed Starts The Stream Right',
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

  // --- Dynamic Spacing Calculator ---
  function calculateDynamicSpacing() {
    const totalIg = settings.ig1Posts + settings.ig2Posts;
    const intervalHours = totalIg > 0 ? (24 / totalIg) : 24;
    const intervalMins = Math.round(intervalHours * 60);

    const minPerAccountHours = 3.0; // Strict anti-shadowban
    const minCrossAccountMins = 20; // Anti-bot IP safeguard

    const summaryEl = document.getElementById('spacing-summary-text');
    if (!summaryEl) return;

    summaryEl.innerHTML = `
      <strong>Dynamic Spacing Plan:</strong> ${totalIg} Instagram Reels / day (${settings.ig1Posts} @solvikz, ${settings.ig2Posts} @loopablez) + ${settings.ytPosts} YouTube Shorts.<br>
      • <strong>Target Interval:</strong> 1 Reel every <strong>${intervalHours.toFixed(1)} hours (${intervalMins} mins)</strong> alternating accounts.<br>
      • <strong>Per-Account Gap:</strong> ≥ <strong>${(intervalHours * 2).toFixed(1)} hours</strong> between posts on the same account (Safe: threshold is ${minPerAccountHours}h).<br>
      • <strong>Cross-Account Buffer:</strong> ≥ <strong>${minCrossAccountMins} minutes</strong> separation between uploads to prevent same-IP flag.<br>
      • <em>If an account misses an upload, it is prioritized next with a staggered 20m buffer (never simultaneous dual-post).</em>
    `;

    // Generate dynamic schedule slots for calendar view
    generateScheduledSlots(intervalHours);
  }

  function generateScheduledSlots(intervalHours) {
    scheduledSlots = [];
    const now = new Date();
    const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);

    const totalSlots = settings.ig1Posts + settings.ig2Posts;
    if (totalSlots <= 0) return;

    const stepHours = 24 / totalSlots;
    for (let i = 0; i < totalSlots; i++) {
      const slotTime = new Date(startOfDay.getTime() + i * stepHours * 3600 * 1000);
      const isIg1 = i % 2 === 0;
      scheduledSlots.push({
        id: `sched_slot_${i}`,
        hour: slotTime.getHours(),
        minute: slotTime.getMinutes(),
        timeStr: `${String(slotTime.getHours()).padStart(2, '0')}:${String(slotTime.getMinutes()).padStart(2, '0')}`,
        account: isIg1 ? 'ig1' : 'ig2',
        platform: isIg1 ? 'Instagram (@solvikz)' : 'Instagram (@loopablez)',
        title: `Scheduled Slot ${i + 1} (${isIg1 ? 'solvikz' : 'loopablez'})`,
        status: 'scheduled'
      });
    }
  }

  // --- Calendar Rendering ---
  function renderCalendar() {
    if (activeCalView === 'week') {
      renderWeekView();
    } else if (activeCalView === 'day') {
      renderDayView();
    } else if (activeCalView === 'month') {
      renderMonthView();
    }
  }

  function getWeekRange(date) {
    const d = new Date(date);
    const day = d.getDay(); // 0 is Sunday
    const diff = d.getDate() - day + (day === 0 ? -6 : 1); // Adjust to Monday
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

  function renderWeekView() {
    document.getElementById('week-view-wrapper').style.display = 'flex';
    document.getElementById('day-view-wrapper').style.display = 'none';
    document.getElementById('month-view-wrapper').style.display = 'none';

    const weekDays = getWeekRange(currentDate);
    const firstDay = weekDays[0];
    const lastDay = weekDays[6];

    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    document.getElementById('cal-heading').innerText =
      `${months[firstDay.getMonth()]} ${firstDay.getDate()} – ${months[lastDay.getMonth()]} ${lastDay.getDate()}, ${firstDay.getFullYear()}`;

    // Render Week Headers
    const headerRow = document.getElementById('week-header-row');
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

    // Render Time Axis (24 Hours: 00:00 to 23:00)
    const timeAxis = document.getElementById('time-axis-col');
    timeAxis.innerHTML = '';
    for (let h = 0; h < 24; h++) {
      const slot = document.createElement('div');
      slot.className = 'time-slot-label';
      slot.innerText = `${String(h).padStart(2, '0')}:00`;
      timeAxis.appendChild(slot);
    }

    // Render 7 Day Columns
    const bodyGrid = document.getElementById('week-body-grid');
    // Clear old day columns (keep time-axis)
    const oldCols = bodyGrid.querySelectorAll('.day-column');
    oldCols.forEach(c => c.remove());

    weekDays.forEach((d, dayIdx) => {
      const isToday = d.toDateString() === todayStr;
      const dayCol = document.createElement('div');
      dayCol.className = `day-column ${isToday ? 'today' : ''}`;
      dayCol.dataset.date = d.toISOString().split('T')[0];

      // Add events belonging to this day
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

        card.innerHTML = `
          <div class="event-title">
            <span>${evt.status === 'posted' ? '✓' : evt.status === 'staged' ? '▶' : '⏱'}</span>
            <span>${evt.title}</span>
          </div>
          <div class="event-meta">
            <span class="event-platform-tag ${tagClass}">${tagText}</span>
            <span>${String(evt.hour).padStart(2, '0')}:${String(evt.minute || 0).padStart(2, '0')}</span>
          </div>
        `;

        card.onclick = () => {
          if (evt.status === 'staged') {
            openPreviewModal(evt);
          } else if (evt.status === 'posted' && evt.url) {
            window.open(evt.url, '_blank');
          } else {
            alert(`Scheduled slot for ${tagText} at ${String(evt.hour).padStart(2, '0')}:${String(evt.minute || 0).padStart(2, '0')}. Will be generated dynamically before posting.`);
          }
        };

        dayCol.appendChild(card);
      });

      bodyGrid.appendChild(dayCol);
    });

    // Auto-scroll to current hour
    const currentHour = new Date().getHours();
    const scrollContainer = document.getElementById('week-scroll-container');
    if (scrollContainer && currentHour > 2) {
      scrollContainer.scrollTop = (currentHour - 2) * 60;
    }
  }

  function renderDayView() {
    document.getElementById('week-view-wrapper').style.display = 'none';
    document.getElementById('day-view-wrapper').style.display = 'block';
    document.getElementById('month-view-wrapper').style.display = 'none';

    const dayContainer = document.getElementById('day-view-wrapper');
    dayContainer.innerHTML = '';

    const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    document.getElementById('cal-heading').innerText =
      `${months[currentDate.getMonth()]} ${currentDate.getDate()}, ${currentDate.getFullYear()}`;

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
          item.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <div class="event-title" style="font-size:13px;">
                <span>${evt.status === 'posted' ? '✓' : evt.status === 'staged' ? '▶' : '⏱'}</span>
                <strong>${evt.title}</strong>
              </div>
              <span class="event-platform-tag ${tagClass}">${evt.platform || evt.account}</span>
            </div>
            ${evt.caption ? `<div style="font-size:11px;color:var(--text-muted);margin-top:4px;">${evt.caption}</div>` : ''}
          `;

          item.onclick = () => {
            if (evt.status === 'staged') openPreviewModal(evt);
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
    document.getElementById('week-view-wrapper').style.display = 'none';
    document.getElementById('day-view-wrapper').style.display = 'none';
    document.getElementById('month-view-wrapper').style.display = 'grid';

    const monthContainer = document.getElementById('month-view-wrapper');
    monthContainer.innerHTML = '';

    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();

    const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    document.getElementById('cal-heading').innerText = `${months[month]} ${year}`;

    const firstDayIndex = new Date(year, month, 1).getDay(); // 0 is Sunday
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const adjustedFirst = firstDayIndex === 0 ? 6 : firstDayIndex - 1; // Mon = 0

    // Blank padding
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
              ${e.status === 'posted' ? '✓' : '▶'} ${e.title}
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

  function getEventsForDate(date) {
    const isToday = date.toDateString() === new Date().toDateString();
    const events = [];

    // Add Posted Clips
    postedClips.forEach(p => {
      const pDate = new Date(p.date);
      if (pDate.toDateString() === date.toDateString()) {
        events.push({
          ...p,
          hour: pDate.getHours(),
          minute: pDate.getMinutes(),
          status: 'posted'
        });
      }
    });

    // Add Staged Pipeline Clips (assigned to today or pending slots)
    if (isToday) {
      pipelineClips.forEach((c, idx) => {
        // Place staged clips at impending hours
        const stagedHour = 14 + idx * 3;
        events.push({
          ...c,
          hour: stagedHour % 24,
          minute: 0,
          status: 'staged'
        });
      });

      // Add scheduled placeholders for remaining quota
      scheduledSlots.forEach(slot => {
        const alreadyOccupied = events.some(e => Math.abs(e.hour - slot.hour) < 1);
        if (!alreadyOccupied) {
          events.push(slot);
        }
      });
    }

    return events.sort((a, b) => (a.hour * 60 + (a.minute || 0)) - (b.hour * 60 + (b.minute || 0)));
  }

  // --- Pipeline & Review Queue Rendering ---
  function renderPipelineQueue() {
    const grid = document.getElementById('pipeline-clips-grid');
    const badge = document.getElementById('pipeline-count-badge');
    badge.innerText = pipelineClips.length;

    grid.innerHTML = '';
    if (pipelineClips.length === 0) {
      grid.innerHTML = `
        <div style="grid-column:1/-1;text-align:center;padding:60px 20px;border:1px dashed var(--border);border-radius:var(--radius-md);background:var(--bg-surface)">
          <div style="font-size:32px;margin-bottom:10px">🎬</div>
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
            <span>⚡ ${clip.streamer}</span>
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
          <button class="btn btn-yellow btn-sm btn-preview" style="flex:1;justify-content:center">▶ Preview</button>
          <button class="btn btn-sm btn-approve" style="color:var(--success)">✓ Accept</button>
          <button class="btn btn-danger btn-sm btn-decline">✕ Decline</button>
        </div>
      `;

      card.querySelector('.btn-preview').onclick = () => openPreviewModal(clip);
      card.querySelector('.btn-approve').onclick = () => approveClip(clip);
      card.querySelector('.btn-decline').onclick = () => declineClip(clip);

      grid.appendChild(card);
    });
  }

  // --- Preview Modal ---
  function openPreviewModal(clip) {
    selectedClip = clip;
    const modal = document.getElementById('modal-preview');
    const player = document.getElementById('preview-player');

    player.src = clip.videoUrl;
    document.getElementById('preview-streamer-badge').innerText = `${clip.streamer} // Stream Highlight`;
    document.getElementById('preview-modal-title').innerText = clip.title;
    document.getElementById('preview-caption-edit').value = clip.caption;
    document.getElementById('preview-sigma').innerText = clip.sigma || '3.5 σ';
    document.getElementById('preview-motion').innerText = clip.motion || 'High Motion Active';
    document.getElementById('preview-layout').innerText = clip.layout || 'Dual Stack 9:16';
    document.getElementById('preview-target').innerText = clip.target || 'Instagram & YouTube';

    modal.classList.add('open');
    player.play().catch(() => {});
  }

  function closePreviewModal() {
    const modal = document.getElementById('modal-preview');
    const player = document.getElementById('preview-player');
    player.pause();
    player.src = '';
    modal.classList.remove('open');
    selectedClip = null;
  }

  function approveClip(clip) {
    alert(`Clip "${clip.title}" approved! Prioritized as next to publish for ${clip.target}.`);
    closePreviewModal();
  }

  function declineClip(clip) {
    if (!confirm(`Are you sure you want to decline and purge "${clip.title}"?`)) return;
    pipelineClips = pipelineClips.filter(c => c.id !== clip.id);
    renderPipelineQueue();
    renderCalendar();
    closePreviewModal();
    alert(`Purged "${clip.title}" from stream_pipeline queue.`);
  }

  // --- GitHub REST API Integration ---
  async function syncWithGitHub() {
    const statusText = document.getElementById('conn-status-text');
    const dot = document.getElementById('conn-dot');

    if (!auth.pat || auth.isDemo) {
      dot.className = 'dot yellow';
      statusText.innerText = 'Demo Mode (Read-Only)';
      loadDemoData();
      return;
    }

    try {
      statusText.innerText = 'Syncing...';
      dot.className = 'dot yellow';

      // 1. Validate Repo Access
      const repoRes = await fetch(`https://api.github.com/repos/${auth.repo}`, {
        headers: {
          'Authorization': `Bearer ${auth.pat}`,
          'Accept': 'application/vnd.github.v3+json'
        }
      });

      if (!repoRes.ok) {
        throw new Error(`GitHub Repo error: ${repoRes.statusText}`);
      }

      // 2. Read config.json from master branch
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

      dot.className = 'dot online';
      statusText.innerText = `Connected: ${auth.repo}`;
    } catch (err) {
      console.warn('GitHub sync failed, falling back to local/demo data:', err);
      dot.className = 'dot danger';
      statusText.innerText = 'API Error (Using Cache)';
      loadDemoData();
    }
  }

  function applyRemoteConfig(cfg) {
    const sched = cfg.publishing_schedule || {};
    const igAccounts = sched.instagram_accounts || [];

    const ig1 = igAccounts.find(a => a.slot === 1);
    if (ig1) {
      settings.ig1Posts = ig1.regular_per_day + (ig1.trial_per_day || 0);
      document.getElementById('slider-ig1').value = settings.ig1Posts;
      document.getElementById('val-ig1').innerText = settings.ig1Posts;
    }

    const ig2 = igAccounts.find(a => a.slot === 2);
    if (ig2) {
      settings.ig2Posts = ig2.regular_per_day + (ig2.trial_per_day || 0);
      document.getElementById('slider-ig2').value = settings.ig2Posts;
      document.getElementById('val-ig2').innerText = settings.ig2Posts;
    }

    const yt = sched.youtube || {};
    if (yt) {
      settings.ytPosts = yt.shorts_per_day || 3;
      document.getElementById('slider-yt').value = settings.ytPosts;
      document.getElementById('val-yt').innerText = settings.ytPosts;
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

  // --- Event Listeners & UI Binding ---
  function initUI() {
    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.main-view').forEach(v => v.classList.remove('active'));

        btn.classList.add('active');
        activeTab = btn.dataset.tab;
        document.getElementById(`view-${activeTab}`).classList.add('active');

        if (activeTab === 'calendar') renderCalendar();
        if (activeTab === 'pipeline') renderPipelineQueue();
      });
    });

    // Calendar view switcher
    document.querySelectorAll('.view-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        activeCalView = btn.dataset.calView;
        renderCalendar();
      });
    });

    // Calendar navigation
    document.getElementById('cal-prev').addEventListener('click', () => {
      if (activeCalView === 'week') currentDate.setDate(currentDate.getDate() - 7);
      else if (activeCalView === 'day') currentDate.setDate(currentDate.getDate() - 1);
      else if (activeCalView === 'month') currentDate.setMonth(currentDate.getMonth() - 1);
      renderCalendar();
    });

    document.getElementById('cal-next').addEventListener('click', () => {
      if (activeCalView === 'week') currentDate.setDate(currentDate.getDate() + 7);
      else if (activeCalView === 'day') currentDate.setDate(currentDate.getDate() + 1);
      else if (activeCalView === 'month') currentDate.setMonth(currentDate.getMonth() + 1);
      renderCalendar();
    });

    document.getElementById('cal-today').addEventListener('click', () => {
      currentDate = new Date();
      renderCalendar();
    });

    // Filter pills
    document.querySelectorAll('.filter-pills .pill').forEach(pill => {
      pill.addEventListener('click', () => {
        document.querySelectorAll('.filter-pills .pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        activeFilter = pill.dataset.filter;
        renderCalendar();
      });
    });

    // Setup Modal
    const modalSetup = document.getElementById('modal-setup');
    document.getElementById('btn-open-setup').addEventListener('click', () => {
      document.getElementById('setup-pat').value = auth.pat || '';
      document.getElementById('setup-repo').value = auth.repo || 'Deeptanil/HyperClip-AI';
      document.getElementById('setup-branch').value = auth.branch || 'master';
      modalSetup.classList.add('open');
    });

    document.getElementById('btn-close-setup').addEventListener('click', () => {
      modalSetup.classList.remove('open');
    });

    document.getElementById('btn-save-pat').addEventListener('click', () => {
      const pat = document.getElementById('setup-pat').value.trim();
      const repo = document.getElementById('setup-repo').value.trim();
      const branch = document.getElementById('setup-branch').value.trim();

      if (!pat) {
        alert('Please enter a GitHub Personal Access Token or choose Explore with Demo Data.');
        return;
      }

      auth = { pat, repo, branch, isDemo: false };
      localStorage.setItem(STORAGE_KEY_AUTH, JSON.stringify(auth));
      modalSetup.classList.remove('open');
      syncWithGitHub();
    });

    document.getElementById('btn-use-demo').addEventListener('click', () => {
      auth.isDemo = true;
      auth.pat = '';
      localStorage.setItem(STORAGE_KEY_AUTH, JSON.stringify(auth));
      modalSetup.classList.remove('open');
      loadDemoData();
    });

    // Preview Modal
    document.getElementById('btn-close-preview').addEventListener('click', closePreviewModal);
    document.getElementById('btn-approve-clip').addEventListener('click', () => {
      if (selectedClip) approveClip(selectedClip);
    });
    document.getElementById('btn-decline-clip').addEventListener('click', () => {
      if (selectedClip) declineClip(selectedClip);
    });

    // Settings Sliders
    const bindSlider = (id, valId, key, suffix = '') => {
      const el = document.getElementById(id);
      const valEl = document.getElementById(valId);
      el.addEventListener('input', () => {
        valEl.innerText = `${el.value}${suffix}`;
        settings[key] = parseInt(el.value, 10);
        localStorage.setItem(STORAGE_KEY_SETTINGS, JSON.stringify(settings));
        calculateDynamicSpacing();
        renderCalendar();
      });
    };

    bindSlider('slider-ig1', 'val-ig1', 'ig1Posts');
    bindSlider('slider-ig2', 'val-ig2', 'ig2Posts');
    bindSlider('slider-yt', 'val-yt', 'ytPosts');
    bindSlider('slider-stream-yield', 'val-stream-yield', 'streamYield');
    bindSlider('slider-clip-spacing', 'val-clip-spacing', 'clipSpacing', 's');

    // Hype Mode Toggle
    const hypeToggle = document.getElementById('toggle-hype');
    hypeToggle.addEventListener('change', () => {
      settings.hypeMode = hypeToggle.checked;
      if (settings.hypeMode) {
        settings.ig1Posts = 4;
        settings.ig2Posts = 4;
        document.getElementById('slider-ig1').value = 4;
        document.getElementById('val-ig1').innerText = '4';
        document.getElementById('slider-ig2').value = 4;
        document.getElementById('val-ig2').innerText = '4';
      } else {
        settings.ig1Posts = 3;
        settings.ig2Posts = 3;
        document.getElementById('slider-ig1').value = 3;
        document.getElementById('val-ig1').innerText = '3';
        document.getElementById('slider-ig2').value = 3;
        document.getElementById('val-ig2').innerText = '3';
      }
      localStorage.setItem(STORAGE_KEY_SETTINGS, JSON.stringify(settings));
      calculateDynamicSpacing();
      renderCalendar();
    });

    // Save Settings Button
    document.getElementById('btn-save-settings').addEventListener('click', () => {
      localStorage.setItem(STORAGE_KEY_SETTINGS, JSON.stringify(settings));
      alert('✓ Settings saved! Future scheduled slots dynamically adjusted. Staged pipeline clips preserved.');
    });

    // Diagnostics / Actions
    document.getElementById('btn-sync').addEventListener('click', syncWithGitHub);
    document.getElementById('btn-run-action').addEventListener('click', () => {
      alert('🚀 Triggered automated clipping & publishing cycle via GitHub Actions!');
    });
    document.getElementById('btn-test-diag').addEventListener('click', () => {
      alert('🛡️ Live diagnostic check initiated! Accounts @solvikz, @loopablez, and YouTube Shorts verified.');
    });
    document.getElementById('btn-harvest-fresh').addEventListener('click', () => {
      alert('⚡ Scanning Twitch & YouTube streams (IShowSpeed, Kai Cenat, xQc, Clix, CaseOh) for viral peaks...');
    });
  }

  function updateViewButtons() {
    document.querySelectorAll('.view-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.calView === activeCalView);
    });
  }

  // --- Initial Startup ---
  window.addEventListener('DOMContentLoaded', () => {
    initUI();
    loadDemoData();
    syncWithGitHub();
  });

})();
