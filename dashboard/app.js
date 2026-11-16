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
    ig1TrialPosts: 2,
    ig2Posts: 3,
    ytPosts: 3,
    hypeMode: false,
    streamYield: 3,
    clipSpacing: 300
  });

  if (typeof settings.ig1TrialPosts === 'undefined') {
    settings.ig1TrialPosts = Math.min(2, settings.ig1Posts || 3);
  }

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

  // --- Demo Dataset (No Emojis, Real Streamer Clips) ---
  const DEMO_PIPELINE = [
    {
      id: 'clip_xqc_cs',
      filename: '2026-11-15-xqc_cs_1v3_clutch.mp4',
      path: 'output/stream_pipeline/2026-11-15-xqc_cs_1v3_clutch.mp4',
      streamer: 'xQc',
      title: 'xQc 1v3 Counter-Strike Clutch',
      caption: 'xQc clutches insane 1v3 live in Counter-Strike! #xqc #cs2 #gaming #twitchclips #shorts',
      duration: '0:38',
      durationSec: 38,
      sigma: '4.8 σ',
      motion: 'Delta 24.1% (High Action)',
      layout: 'Dual Stack 9:16',
      target: 'Instagram (loopablez)',
      account: 'ig2',
      isTrial: false,
      status: 'staged',
      videoUrl: 'https://raw.githubusercontent.com/Deeptanil/HyperClip-AI/content/output/stream_pipeline/2026-11-15-xqc_cs_1v3_clutch.mp4'
    },
    {
      id: 'clip_kai_malenia',
      filename: '2026-11-15-kai_cenat_malenia_clutch.mp4',
      path: 'output/stream_pipeline/2026-11-15-kai_cenat_malenia_clutch.mp4',
      streamer: 'Kai Cenat',
      title: 'Kai Cenat Beats Malenia After 431 Deaths',
      caption: 'After 431+ attempts and 50+ hours Kai Cenat finally defeats Malenia live on stream! #kaicenat #eldenring #malenia #twitchclips #gaming #shorts #reels',
      duration: '0:28',
      durationSec: 28,
      sigma: '4.9 σ',
      motion: 'Delta 28.5% (Victory Moment)',
      layout: 'Dual Stack 9:16',
      target: 'Instagram (solvikz) [Trial Reel] & YouTube',
      account: 'ig1',
      isTrial: true,
      status: 'staged',
      videoUrl: 'https://raw.githubusercontent.com/Deeptanil/HyperClip-AI/content/output/stream_pipeline/2026-11-15-kai_cenat_malenia_clutch.mp4'
    },
    {
      id: 'clip_caseoh_terror',
      filename: '2026-11-15-caseoh_lethal_company_scream.mp4',
      path: 'output/stream_pipeline/2026-11-15-caseoh_lethal_company_scream.mp4',
      streamer: 'CaseOh',
      title: 'CaseOh Terrified on Lethal Company',
      caption: 'CaseOh cannot survive 5 minutes in Lethal Company facility! #caseoh #lethalcompany #gaming #twitchclips #shorts',
      duration: '0:32',
      durationSec: 32,
      sigma: '4.5 σ',
      motion: 'Delta 21.0% (Terrified)',
      layout: 'Dual Stack 9:16',
      target: 'YouTube Shorts',
      account: 'youtube',
      isTrial: false,
      status: 'staged',
      videoUrl: 'https://raw.githubusercontent.com/Deeptanil/HyperClip-AI/content/output/stream_pipeline/2026-11-15-caseoh_lethal_company_scream.mp4'
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
      const trial1 = settings.ig1TrialPosts || 0;
      const reg1 = Math.max(0, settings.ig1Posts - trial1);
      summaryEl.innerHTML = `
        <strong>Dynamic Spacing Plan:</strong> ${totalIg} Instagram Reels / day (${settings.ig1Posts} @solvikz [${trial1} trial, ${reg1} standard] + ${settings.ig2Posts} @loopablez) + ${settings.ytPosts} YouTube Shorts.<br>
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

    generateScheduledSlots();
  }

  function generateScheduledSlots() {
    scheduledSlots = [];
    const ig1Count = Math.max(0, parseInt(settings.ig1Posts, 10) || 0);
    const ig2Count = Math.max(0, parseInt(settings.ig2Posts, 10) || 0);
    const ytCount = Math.max(0, parseInt(settings.ytPosts, 10) || 0);

    const totalIg = ig1Count + ig2Count;

    // 1. Instagram Slots: Interleave ig1 and ig2 spaced across 24h
    if (totalIg > 0) {
      const stepMinutes = Math.floor((24 * 60) / totalIg);
      let ig1Allocated = 0;
      let ig1TrialAllocated = 0;
      let ig2Allocated = 0;
      const ig1TrialTarget = Math.max(0, parseInt(settings.ig1TrialPosts, 10) || 0);

      for (let i = 0; i < totalIg; i++) {
        const totalMinutes = i * stepMinutes;
        const h = Math.floor(totalMinutes / 60) % 24;
        const m = totalMinutes % 60;

        let acc = 'ig1';
        if (ig1Allocated < ig1Count && ig2Allocated < ig2Count) {
          acc = (i % 2 === 0) ? 'ig1' : 'ig2';
        } else if (ig1Allocated < ig1Count) {
          acc = 'ig1';
        } else {
          acc = 'ig2';
        }

        let isTrial = false;
        if (acc === 'ig1') {
          ig1Allocated++;
          if (ig1TrialAllocated < ig1TrialTarget) {
            isTrial = true;
            ig1TrialAllocated++;
          }
        } else {
          ig2Allocated++;
        }

        const isIg1 = acc === 'ig1';
        scheduledSlots.push({
          id: `sched_ig_${i}`,
          hour: h,
          minute: m,
          timeMinutes: totalMinutes,
          timeStr: `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`,
          account: acc,
          platform: isIg1 ? 'Instagram (@solvikz)' : 'Instagram (@loopablez)',
          title: isTrial ? `Scheduled Trial Reel (${isIg1 ? 'solvikz' : 'loopablez'})` : `Scheduled Reel (${isIg1 ? 'solvikz' : 'loopablez'})`,
          status: 'scheduled',
          isTrial: isTrial
        });
      }
    }

    // 2. YouTube Shorts Slots: Spaced across 24h, intelligently staggered from IG slots
    if (ytCount > 0) {
      const stepYt = Math.floor((24 * 60) / ytCount);
      const igMinutes = scheduledSlots.map(s => s.timeMinutes);

      // Find an offset that maximizes circular distance to all existing Instagram slots
      let bestOffset = Math.floor(stepYt / 2);
      let maxMinDist = -1;
      for (let candOffset = 15; candOffset < stepYt; candOffset += 15) {
        let minDist = 9999;
        for (let j = 0; j < ytCount; j++) {
          const ytM = (j * stepYt + candOffset) % (24 * 60);
          for (const igM of igMinutes) {
            const diff = Math.abs(ytM - igM);
            const circDist = Math.min(diff, 1440 - diff);
            if (circDist < minDist) minDist = circDist;
          }
        }
        if (minDist > maxMinDist) {
          maxMinDist = minDist;
          bestOffset = candOffset;
        }
      }

      for (let j = 0; j < ytCount; j++) {
        const totalMinutes = (j * stepYt + bestOffset) % (24 * 60);
        const h = Math.floor(totalMinutes / 60) % 24;
        const m = totalMinutes % 60;

        scheduledSlots.push({
          id: `sched_yt_${j}`,
          hour: h,
          minute: m,
          timeMinutes: totalMinutes,
          timeStr: `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`,
          account: 'youtube',
          platform: 'YouTube Shorts',
          title: `Scheduled YouTube Short ${j + 1}`,
          status: 'scheduled'
        });
      }
    }

    // Sort chronologically
    scheduledSlots.sort((a, b) => a.timeMinutes - b.timeMinutes);
  }

  // --- Calendar View Logic (Rolling 7-Day View: Today in Second Column) ---
  function getWeekRange(anchorDate) {
    // Column 0 = anchorDate - 1 day (Yesterday)
    // Column 1 = anchorDate (Today, second column)
    // Columns 2..6 = anchorDate + 1..5 days (Next 5 days)
    const base = new Date(anchorDate.getFullYear(), anchorDate.getMonth(), anchorDate.getDate(), 0, 0, 0);

    const days = [];
    for (let offset = -1; offset <= 5; offset++) {
      const d = new Date(base);
      d.setDate(base.getDate() + offset);
      days.push(d);
    }
    return days;
  }

  // --- Dynamic Multi-Lane Clustering for Overlapping Events ---
  function layoutEventsWithLanes(events) {
    events.forEach(e => {
      e.startMinutes = e.hour * 60 + (e.minute || 0);
      const durMins = Math.max(54, e.durationSec ? Math.ceil(e.durationSec / 60) : 54);
      e.endMinutes = e.startMinutes + durMins;
    });

    const sorted = [...events].sort((a, b) => a.startMinutes - b.startMinutes || (b.endMinutes - b.startMinutes) - (a.endMinutes - a.startMinutes));

    // Group overlapping events into clusters
    const clusters = [];
    let curCluster = [];
    let curEnd = -1;

    sorted.forEach(ev => {
      if (curCluster.length === 0) {
        curCluster.push(ev);
        curEnd = ev.endMinutes;
      } else if (ev.startMinutes < curEnd) {
        curCluster.push(ev);
        curEnd = Math.max(curEnd, ev.endMinutes);
      } else {
        clusters.push(curCluster);
        curCluster = [ev];
        curEnd = ev.endMinutes;
      }
    });
    if (curCluster.length > 0) {
      clusters.push(curCluster);
    }

    // Allocate lane columns in each cluster
    clusters.forEach(cluster => {
      const laneEndTimes = [];
      cluster.forEach(ev => {
        let placed = false;
        for (let l = 0; l < laneEndTimes.length; l++) {
          if (laneEndTimes[l] <= ev.startMinutes) {
            laneEndTimes[l] = ev.endMinutes;
            ev.lane = l;
            placed = true;
            break;
          }
        }
        if (!placed) {
          ev.lane = laneEndTimes.length;
          laneEndTimes.push(ev.endMinutes);
        }
      });

      const totalLanes = Math.max(1, laneEndTimes.length);
      cluster.forEach(ev => {
        ev.totalLanes = totalLanes;
      });
    });

    return sorted;
  }

  function getEventsForDate(targetDate) {
    const now = new Date();
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);
    const targetMidnight = new Date(targetDate.getFullYear(), targetDate.getMonth(), targetDate.getDate(), 0, 0, 0);

    const isToday = targetMidnight.getTime() === startOfToday.getTime();
    const isPast = targetMidnight.getTime() < startOfToday.getTime();
    const isFuture = targetMidnight.getTime() > startOfToday.getTime();
    const events = [];

    // 1. Posted archive clips
    postedClips.forEach(p => {
      const pDate = new Date(p.date);
      if (pDate.toDateString() === targetDate.toDateString()) {
        const acc = (p.account === 'yt') ? 'youtube' : p.account;
        events.push({
          ...p,
          account: acc,
          hour: pDate.getHours(),
          minute: pDate.getMinutes(),
          timeMinutes: pDate.getHours() * 60 + pDate.getMinutes(),
          status: 'posted'
        });
      }
    });

    // In the past: ONLY show real posted clips! Never show scheduled placeholder slots.
    if (isPast) {
      return events.sort((a, b) => a.timeMinutes - b.timeMinutes);
    }

    // 2. Today:
    if (isToday) {
      const currentMinutes = now.getHours() * 60 + now.getMinutes();

      const todayPostedCount = { ig1: 0, ig2: 0, youtube: 0 };
      const lastPostMinutes = { ig1: -9999, ig2: -9999, youtube: -9999 };

      events.forEach(e => {
        if (e.status === 'posted') {
          const acc = (e.account === 'yt') ? 'youtube' : e.account;
          todayPostedCount[acc] = (todayPostedCount[acc] || 0) + 1;
          if (e.timeMinutes > lastPostMinutes[acc]) {
            lastPostMinutes[acc] = e.timeMinutes;
          }
        }
      });

      // Filter upcoming slots that are valid:
      // - Must not have already passed in time (skip missed / late slots)
      // - Must not exceed daily limit for that account if already satisfied by real posts
      // - Must not collide with a real post within 90 minutes
      // - Must respect strict 3.0h anti-spam cooldown if account posted late
      const upcomingSlots = [];

      scheduledSlots.forEach(slot => {
        const slotMinutes = slot.hour * 60 + slot.minute;
        const acc = (slot.account === 'yt') ? 'youtube' : slot.account;
        const maxDaily = acc === 'ig1' ? settings.ig1Posts : acc === 'ig2' ? settings.ig2Posts : settings.ytPosts;

        // Skip slot if its scheduled time has already passed today
        if (slotMinutes < currentMinutes) {
          return;
        }

        // Skip if daily quota for this account is already fulfilled by real posts
        if (todayPostedCount[acc] >= maxDaily) {
          return;
        }

        // If a real post on this account happened close to this slot, suppress the slot
        const hasNearbyPost = events.some(e => e.status === 'posted' && e.account === acc && Math.abs(e.timeMinutes - slotMinutes) < 90);
        if (hasNearbyPost) {
          return;
        }

        // Strict anti-shadowban cooldown check (3.0h for Instagram, 1.0h for YouTube)
        const minGap = (acc === 'youtube') ? 60 : 180;
        if (lastPostMinutes[acc] >= 0 && slotMinutes < (lastPostMinutes[acc] + minGap)) {
          // Account posted late and is still on mandatory cooldown. Skip this slot!
          return;
        }

        upcomingSlots.push({ ...slot });
      });

      // Map staged pipeline clips onto the earliest upcoming slots
      let stagedIdx = 0;
      upcomingSlots.forEach(slot => {
        if (stagedIdx < pipelineClips.length) {
          const stagedClip = pipelineClips[stagedIdx];
          events.push({
            ...stagedClip,
            account: slot.account,
            platform: slot.platform,
            hour: slot.hour,
            minute: slot.minute,
            timeMinutes: slot.hour * 60 + slot.minute,
            status: 'staged'
          });
          stagedIdx++;
        } else {
          events.push({
            ...slot,
            timeMinutes: slot.hour * 60 + slot.minute,
            date: targetDate.toISOString()
          });
        }
      });

      // Mark the immediate next upcoming event (staged or scheduled)
      const upcomingEvents = events.filter(e => e.timeMinutes >= currentMinutes);
      if (upcomingEvents.length > 0) {
        upcomingEvents.sort((a, b) => a.timeMinutes - b.timeMinutes);
        upcomingEvents[0].isNext = true;
      }
    }

    // 3. Future Days:
    if (isFuture) {
      scheduledSlots.forEach(slot => {
        events.push({
          ...slot,
          timeMinutes: slot.hour * 60 + slot.minute,
          date: targetDate.toISOString()
        });
      });
    }

    return events.sort((a, b) => a.timeMinutes - b.timeMinutes);
  }

  function matchesFilter(evt) {
    if (activeFilter === 'all') return true;
    if (activeFilter === 'staged') return evt.status === 'staged';
    const acc = (evt.account === 'yt') ? 'youtube' : evt.account;
    return acc === activeFilter;
  }

  function renderCalendar() {
    if (activeCalView === 'week') renderWeekView();
    else if (activeCalView === 'day') renderDayView();
    else if (activeCalView === 'month') renderMonthView();
  }

  function updateCurrentTimeIndicator() {
    const timeLine = document.getElementById('cal-current-time-line');
    const badge = document.getElementById('cal-current-time-badge');
    if (!timeLine) return;

    const now = new Date();
    const currentMinutes = now.getHours() * 60 + now.getMinutes();
    timeLine.style.top = `${currentMinutes}px`;
    timeLine.style.display = 'block';

    if (badge) {
      badge.innerText = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
    }
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

    // Render Headers (Rolling 7-day: Col 0 = Yesterday, Col 1 = Today, Cols 2..6 = Next 5 days)
    const headerRow = document.getElementById('week-header-row');
    if (headerRow) {
      headerRow.innerHTML = '<div class="col-header time-label-spacer">TIME</div>';
      const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
      const todayStr = new Date().toDateString();

      weekDays.forEach(d => {
        const isToday = d.toDateString() === todayStr;
        const col = document.createElement('div');
        col.className = `col-header ${isToday ? 'today' : ''}`;
        col.innerHTML = `
          <div class="day-label">${dayNames[d.getDay()]}</div>
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

    // Render Day Columns with Overlapping Multi-Lane Layout & Smooth Slide
    const bodyGrid = document.getElementById('week-body-grid');
    if (bodyGrid) {
      // Trigger smooth slide transition
      bodyGrid.classList.remove('week-anim-slide');
      void bodyGrid.offsetWidth; // Force reflow
      bodyGrid.classList.add('week-anim-slide');

      const oldCols = bodyGrid.querySelectorAll('.day-column');
      oldCols.forEach(c => c.remove());

      const todayStr = new Date().toDateString();

      weekDays.forEach(d => {
        const isToday = d.toDateString() === todayStr;
        const dayCol = document.createElement('div');
        dayCol.className = `day-column ${isToday ? 'today' : ''}`;
        dayCol.dataset.date = d.toISOString().split('T')[0];

        const rawEvents = getEventsForDate(d).filter(matchesFilter);
        const dayEvents = layoutEventsWithLanes(rawEvents);

        dayEvents.forEach(evt => {
          const acc = (evt.account === 'yt') ? 'youtube' : (evt.account || 'ig1');
          const card = document.createElement('div');
          card.className = `event-card ${evt.status} account-${acc} ${evt.isNext ? 'is-next' : ''}`;
          const topPx = (evt.hour + (evt.minute || 0) / 60) * 60;
          const heightPx = Math.max(54, (evt.durationSec ? (evt.durationSec / 60) * 60 : 54));

          card.style.top = `${topPx}px`;
          card.style.height = `${heightPx}px`;

          // Handle multi-lane side-by-side positioning for overlapping cards
          if (evt.totalLanes > 1) {
            const lanePct = 100 / evt.totalLanes;
            card.classList.add('compact-lane');
            card.style.setProperty('left', `calc(${evt.lane * lanePct}% + 1px)`, 'important');
            card.style.setProperty('width', `calc(${lanePct}% - 2px)`, 'important');
            card.style.setProperty('right', 'auto', 'important');
            card.style.setProperty('z-index', `${10 + evt.lane}`);
          } else {
            card.style.setProperty('left', '3px', 'important');
            card.style.setProperty('width', 'calc(100% - 6px)', 'important');
            card.style.setProperty('right', 'auto', 'important');
            card.style.setProperty('z-index', '10');
          }

          const isCompact = evt.totalLanes > 1;
          const tagClass = acc === 'ig1' ? 'tag-ig1' : acc === 'ig2' ? 'tag-ig2' : 'tag-yt';
          const tagText = isCompact
            ? (acc === 'ig1' ? '@solvikz' : acc === 'ig2' ? '@loop' : 'YT Shorts')
            : (acc === 'ig1' ? '@solvikz' : acc === 'ig2' ? '@loopablez' : 'YouTube Shorts');
          const statusIcon = evt.status === 'posted' ? ICONS.check : evt.status === 'staged' ? ICONS.play : ICONS.clock;
          const timeStr = `${String(evt.hour).padStart(2, '0')}:${String(evt.minute || 0).padStart(2, '0')}`;

          card.title = `${evt.title} // ${acc === 'ig1' ? '@solvikz' : acc === 'ig2' ? '@loopablez' : 'YouTube Shorts'} (${timeStr})`;

          card.innerHTML = `
            <div class="event-title">
              <span class="status-icon">${statusIcon}</span>
              <span class="title-text">${evt.title}</span>
            </div>
            <div class="event-footer">
              <span class="event-account-tag ${tagClass}">${tagText}</span>
              <div class="event-footer-right">
                ${evt.isTrial ? '<span class="badge-trial">TRIAL</span>' : ''}
                ${evt.isNext ? '<span class="badge-next">NEXT</span>' : ''}
                <span class="event-time">${timeStr}</span>
              </div>
            </div>
          `;

          card.onclick = () => {
            if (evt.status === 'staged') {
              window.openPreviewModal(evt);
            } else if (evt.status === 'posted' && evt.url) {
              window.open(evt.url, '_blank');
            } else {
              alert(`Scheduled slot for ${tagText} at ${timeStr}. Will generate dynamically before publication.`);
            }
          };

          dayCol.appendChild(card);
        });

        bodyGrid.appendChild(dayCol);
      });
    }

    updateCurrentTimeIndicator();

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

      const hourEvents = events.filter(e => e.hour === h && matchesFilter(e));
      if (hourEvents.length === 0) {
        content.innerHTML = '<span class="empty-slot">No posts scheduled</span>';
      } else {
        hourEvents.forEach(evt => {
          const acc = (evt.account === 'yt') ? 'youtube' : (evt.account || 'ig1');
          const item = document.createElement('div');
          item.className = `event-card ${evt.status} account-${acc} ${evt.isNext ? 'is-next' : ''}`;
          item.style.position = 'static';
          item.style.height = 'auto';
          item.style.padding = '10px 14px';
          item.style.marginBottom = '6px';

          const tagClass = acc === 'ig1' ? 'tag-ig1' : acc === 'ig2' ? 'tag-ig2' : 'tag-yt';
          const tagText = acc === 'ig1' ? '@solvikz' : acc === 'ig2' ? '@loopablez' : 'YouTube Shorts';
          const statusIcon = evt.status === 'posted' ? ICONS.check : evt.status === 'staged' ? ICONS.play : ICONS.clock;
          const timeStr = `${String(evt.hour).padStart(2, '0')}:${String(evt.minute || 0).padStart(2, '0')}`;

          item.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
              <div class="event-title" style="font-size:13px;">
                <span class="status-icon">${statusIcon}</span>
                <strong class="title-text">${evt.title}</strong>
              </div>
              <div style="display:flex;align-items:center;gap:6px;">
                ${evt.isTrial ? '<span class="badge-trial">TRIAL REEL</span>' : ''}
                ${evt.isNext ? '<span class="badge-next">NEXT UP</span>' : ''}
                <span style="font-size:11px;font-family:var(--font-mono);color:var(--text-dim);">${timeStr}</span>
              </div>
            </div>
            ${evt.caption ? `<div style="font-size:11px;color:var(--text-muted);margin-bottom:6px;">${evt.caption}</div>` : ''}
            <div class="event-footer">
              <span class="event-account-tag ${tagClass}">${tagText}</span>
              <span style="font-size:10px;color:var(--text-dim);text-transform:uppercase;font-family:var(--font-mono);">${evt.status}</span>
            </div>
          `;

          item.onclick = () => {
            if (evt.status === 'staged') window.openPreviewModal(evt);
            else if (evt.status === 'posted' && evt.url) window.open(evt.url, '_blank');
            else alert(`Scheduled slot for ${tagText} at ${timeStr}. Will generate dynamically before publication.`);
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

      const events = getEventsForDate(cellDate).filter(matchesFilter);

      cell.innerHTML = `
        <div class="month-cell-header">
          <span>${d}</span>
          ${events.length > 0 ? `<small style="font-size:10px;color:var(--yellow);font-weight:800;">${events.length} posts</small>` : ''}
        </div>
        <div class="month-badge-strip">
          ${events.slice(0, 3).map(e => {
            const acc = (e.account === 'yt') ? 'youtube' : (e.account || 'ig1');
            const icon = e.status === 'posted' ? ICONS.check : e.status === 'staged' ? ICONS.play : ICONS.clock;
            return `
              <div class="event-card ${e.status} account-${acc}" style="position:static;padding:2px 5px;font-size:9px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:2px;">
                ${icon} ${e.isTrial ? '<span style="color:var(--yellow);font-weight:800">[TRIAL]</span> ' : ''}${e.title}
              </div>
            `;
          }).join('')}
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

    let ig1TrialUsed = 0;
    const ig1TrialLimit = Math.max(0, parseInt(settings.ig1TrialPosts, 10) || 0);

    pipelineClips.forEach(clip => {
      const isIg1 = clip.account === 'ig1' || (clip.target && clip.target.toLowerCase().includes('solvikz'));
      let isTrial = Boolean(clip.isTrial || clip.post_kind === 'trial' || clip.trial || (clip.target && clip.target.toLowerCase().includes('trial')));
      if (!isTrial && isIg1 && ig1TrialUsed < ig1TrialLimit) {
        isTrial = true;
      }
      if (isTrial && isIg1) {
        ig1TrialUsed++;
      }
      clip.isTrial = isTrial;

      const card = document.createElement('div');
      card.className = 'clip-card';

      card.innerHTML = `
        <div class="clip-preview-container">
          <video src="${clip._blobUrl || clip.videoUrl || ('media/' + clip.filename)}" onerror="if(!this.dataset.triedLocal){this.dataset.triedLocal=1;this.src='media/${clip.filename}';}" preload="metadata" muted playsinline></video>
          <div class="clip-overlay-badge">
            <span>${clip.streamer}</span>
          </div>
          ${isTrial ? '<div style="position:absolute;bottom:8px;left:8px;z-index:2;"><span class="clip-trial-tag">TRIAL REEL</span></div>' : ''}
          <div class="clip-duration-badge">${clip.duration}</div>
        </div>
        <div class="clip-body">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:6px;">
            <div class="clip-title">${clip.title}</div>
            <div style="display:flex;gap:4px;align-items:center;">
              ${isTrial ? '<span class="clip-trial-tag">TRIAL REEL</span>' : ''}
              <span class="status-pill" style="font-size:9px;white-space:nowrap;${clip.approval_status === 'approved' ? 'color:var(--success);border-color:rgba(34,197,94,0.4);' : clip.approval_status === 'denied' ? 'color:var(--danger);border-color:rgba(239,68,68,0.4);' : 'color:var(--yellow);'}">
                ${clip.approval_status === 'approved' ? 'Approved' : clip.approval_status === 'denied' ? 'Denied' : 'Pending (Auto)'}
              </span>
            </div>
          </div>
          <div class="clip-caption">${clip.caption}</div>
          <div class="clip-metrics">
            <span>Spike: ${clip.sigma}</span> • 
            <span>${clip.motion}</span> • 
            <span>${clip.post_to_yt ? '<strong style="color:#ffffff">IG + YouTube</strong>' : '<span style="color:var(--text-muted)">Instagram Only (YT Skipped)</span>'}</span>
            ${isTrial ? ' • <span style="color:var(--yellow);font-weight:700">Trial Reel (Non-Followers)</span>' : ''}
          </div>
        </div>
        <div class="clip-actions">
          <button class="btn btn-yellow btn-sm btn-preview" style="flex:1;justify-content:center">Preview</button>
          <button class="btn btn-sm btn-approve" style="color:var(--success)" title="Approve & prioritize">Approve</button>
          <button class="btn btn-warning btn-sm btn-deny" title="Deny clip (removes from pipeline)">Deny</button>
          <button class="btn btn-danger btn-sm btn-delete" title="Permanently delete clip">Delete</button>
        </div>
      `;

      card.querySelector('.btn-preview').onclick = () => window.openPreviewModal(clip);
      card.querySelector('.btn-approve').onclick = () => approveClip(clip, false);
      card.querySelector('.btn-deny').onclick = () => denyClip(clip);
      card.querySelector('.btn-delete').onclick = () => deleteClip(clip);

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
    const contentBranchEl = document.getElementById('setup-content-branch');

    if (patEl) patEl.value = auth.pat || '';
    if (repoEl) repoEl.value = auth.repo || 'Deeptanil/HyperClip-AI';
    if (branchEl) branchEl.value = auth.branch || 'master';
    if (contentBranchEl) contentBranchEl.value = auth.contentBranch || 'content';

    modal.classList.add('open');
  };

  window.closeSetupModal = function () {
    const modal = document.getElementById('modal-setup');
    if (modal) modal.classList.remove('open');
  };

  let activePreviewSessionId = 0;

  window.openPreviewModal = async function (clip) {
    const currentSession = ++activePreviewSessionId;
    selectedClip = clip;
    const modal = document.getElementById('modal-preview');
    const player = document.getElementById('preview-player');
    if (!modal || !player) return;

    // Immediately stop old video, detach error listeners, blank video surface, and show loader
    player.pause();
    player.onerror = null;
    player.oncanplay = null;
    player.onloadeddata = null;
    player.removeAttribute('src');
    player.load();
    player.style.opacity = '0';

    const loader = document.getElementById('preview-video-loader');
    const errorEl = document.getElementById('preview-video-error');
    if (loader) loader.style.display = 'flex';
    if (errorEl) errorEl.style.display = 'none';

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

    const trialPill = document.getElementById('preview-trial-pill');
    const postFormat = document.getElementById('preview-post-format');
    if (trialPill) {
      trialPill.style.display = clip.isTrial ? 'inline-flex' : 'none';
    }
    if (postFormat) {
      postFormat.innerHTML = clip.isTrial 
        ? '<span class="clip-trial-tag" style="margin-right:4px;">TRIAL REEL</span> Tests reach with non-followers'
        : 'Standard Feed Reel (Followers & Explore)';
    }

    modal.classList.add('open');

    // Secure streaming loader: If authenticated to GitHub, stream binary via Blob URL
    // This allows private repository MP4s to play seamlessly in HTML5 <video> without auth blocks!
    if (auth.pat && !auth.isDemo && clip.path) {
      try {
        if (!clip._blobUrl) {
          const res = await fetch(`https://api.github.com/repos/${auth.repo}/contents/${clip.path}?ref=${auth.contentBranch || 'content'}`, {
            headers: {
              'Authorization': `token ${auth.pat.trim()}`,
              'Accept': 'application/vnd.github.v3.raw'
            }
          });
          if (currentSession !== activePreviewSessionId) return;
          if (res.ok) {
            const blob = await res.blob();
            if (currentSession !== activePreviewSessionId) return;
            clip._blobUrl = URL.createObjectURL(blob);
          }
        }
      } catch (err) {
        console.warn('Blob stream fallback to direct URL:', err);
      }
    }

    if (currentSession !== activePreviewSessionId) return;

    // Build candidate source list with local and remote fallbacks
    const candidates = [];
    if (clip._blobUrl) candidates.push(clip._blobUrl);
    if (clip.filename) {
      candidates.push(`media/${clip.filename}`);
      candidates.push(`output/stream_pipeline/${clip.filename}`);
      candidates.push(`../output/stream_pipeline/${clip.filename}`);
    }
    if (clip.videoUrl) candidates.push(clip.videoUrl);

    let candidateIdx = 0;
    function loadNextSource() {
      if (currentSession !== activePreviewSessionId) return;
      if (candidateIdx >= candidates.length) {
        console.warn('All playback sources exhausted for clip:', clip.title);
        const lEl = document.getElementById('preview-video-loader');
        const errEl = document.getElementById('preview-video-error');
        if (lEl) lEl.style.display = 'none';
        if (errEl) errEl.style.display = 'flex';
        player.style.opacity = '0';
        return;
      }
      const nextSrc = candidates[candidateIdx++];
      player.src = nextSrc;
      player.load();
      player.play().catch(() => {});
    }

    player.oncanplay = function () {
      if (currentSession !== activePreviewSessionId) return;
      const lEl = document.getElementById('preview-video-loader');
      const errEl = document.getElementById('preview-video-error');
      if (lEl) lEl.style.display = 'none';
      if (errEl) errEl.style.display = 'none';
      player.style.opacity = '1';
    };

    player.onerror = function (e) {
      if (currentSession !== activePreviewSessionId) return;
      console.warn('Source playback failed, falling back to next candidate:', player.src);
      loadNextSource();
    };

    loadNextSource();
  };

  window.closePreviewModal = function () {
    activePreviewSessionId++; // Invalidate any running session
    const modal = document.getElementById('modal-preview');
    const player = document.getElementById('preview-player');
    if (player) {
      player.pause();
      player.onerror = null; // Detach error listener to prevent re-triggering loadNextSource
      player.oncanplay = null;
      player.onloadeddata = null;
      player.removeAttribute('src');
      player.load();
      player.style.opacity = '0';
    }
    const loader = document.getElementById('preview-video-loader');
    const errorEl = document.getElementById('preview-video-error');
    if (loader) loader.style.display = 'none';
    if (errorEl) errorEl.style.display = 'none';
    const captionEl = document.getElementById('preview-caption-edit');
    if (captionEl) captionEl.value = '';
    if (modal) modal.classList.remove('open');
    selectedClip = null;
  };

  async function updateGitHubClipMetadata(clip, updates) {
    if (!auth.pat || auth.isDemo || !clip.jsonPath || !clip.jsonSha) return;
    try {
      const headers = {
        'Authorization': `token ${auth.pat.trim()}`,
        'Accept': 'application/vnd.github.v3+json'
      };
      const cBranch = auth.contentBranch || 'content';
      const getRes = await fetch(`https://api.github.com/repos/${auth.repo}/contents/${clip.jsonPath}?ref=${cBranch}`, { headers });
      if (!getRes.ok) return;
      const getData = await getRes.json();
      const currentContent = JSON.parse(decodeURIComponent(escape(atob(getData.content))));

      const merged = { ...currentContent, ...updates };
      const newBase64 = btoa(unescape(encodeURIComponent(JSON.stringify(merged, null, 2))));

      const putRes = await fetch(`https://api.github.com/repos/${auth.repo}/contents/${clip.jsonPath}`, {
        method: 'PUT',
        headers,
        body: JSON.stringify({
          message: `chore: update clip status to ${updates.approval_status} for ${clip.filename}`,
          content: newBase64,
          sha: getData.sha,
          branch: cBranch
        })
      });
      if (putRes.ok) {
        const putData = await putRes.json();
        clip.jsonSha = putData.content.sha;
      }
    } catch (e) {
      console.warn('Failed to update GitHub clip metadata:', e);
    }
  }

  function approveClip(clip, isFromModal = false) {
    let newCaption = clip.caption;
    // Only update caption from input if explicitly edited inside the active preview modal
    if (isFromModal && selectedClip && selectedClip.id === clip.id) {
      const captionEl = document.getElementById('preview-caption-edit');
      if (captionEl && captionEl.value.trim()) {
        newCaption = captionEl.value.trim();
      }
    }
    clip.caption = newCaption;
    clip.approval_status = 'approved';
    updateGitHubClipMetadata(clip, { approval_status: 'approved', caption: newCaption });
    renderPipelineQueue();
    renderCalendar();
    alert(`Clip "${clip.title}" approved and prioritized for next upload.`);
    window.closePreviewModal();
  }

  function denyClip(clip) {
    clip.approval_status = 'denied';
    updateGitHubClipMetadata(clip, { approval_status: 'denied' });
    pipelineClips = pipelineClips.filter(c => c.id !== clip.id);
    renderPipelineQueue();
    renderCalendar();
    alert(`Clip "${clip.title}" denied. It has been removed from the publishing queue.`);
    window.closePreviewModal();
  }

  async function deleteClip(clip) {
    if (!confirm(`Are you sure you want to permanently delete "${clip.title}" from storage?`)) return;

    if (auth.pat && !auth.isDemo && clip.path && clip.sha) {
      try {
        const headers = {
          'Authorization': `token ${auth.pat.trim()}`,
          'Accept': 'application/vnd.github.v3+json'
        };
        const cBranch = auth.contentBranch || 'content';

        // Delete MP4 from GitHub
        await fetch(`https://api.github.com/repos/${auth.repo}/contents/${clip.path}`, {
          method: 'DELETE',
          headers,
          body: JSON.stringify({
            message: `chore: purge clip ${clip.filename} via dashboard`,
            sha: clip.sha,
            branch: cBranch
          })
        });

        // Delete matching JSON if exists
        if (clip.jsonPath && clip.jsonSha) {
          await fetch(`https://api.github.com/repos/${auth.repo}/contents/${clip.jsonPath}`, {
            method: 'DELETE',
            headers,
            body: JSON.stringify({
              message: `chore: purge metadata for ${clip.filename} via dashboard`,
              sha: clip.jsonSha,
              branch: cBranch
            })
          });
        }
      } catch (e) {
        console.warn('GitHub remote file deletion error:', e);
      }
    }

    pipelineClips = pipelineClips.filter(c => c.id !== clip.id);
    renderPipelineQueue();
    renderCalendar();
    window.closePreviewModal();
  }

  // --- Real GitHub REST API Integration & Data Engine ---
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
      if (statusText) statusText.innerText = 'Connecting to GitHub...';
      if (dot) dot.className = 'dot yellow';

      const cleanPat = auth.pat.trim();
      const headers = {
        'Authorization': `token ${cleanPat}`,
        'Accept': 'application/vnd.github.v3+json'
      };

      // 1. Verify Repository Access
      const repoRes = await fetch(`https://api.github.com/repos/${auth.repo}`, { headers });
      if (!repoRes.ok) {
        const errJson = await repoRes.json().catch(() => ({}));
        throw new Error(errJson.message || `Repository access failed (${repoRes.status})`);
      }

      // 2. Fetch config.json from production branch (master)
      const pBranch = auth.branch || 'master';
      const configRes = await fetch(`https://api.github.com/repos/${auth.repo}/contents/config.json?ref=${pBranch}`, { headers });
      if (configRes.ok) {
        const configData = await configRes.json();
        const contentStr = decodeURIComponent(escape(atob(configData.content)));
        const configJson = JSON.parse(contentStr);
        applyRemoteConfig(configJson);
      }

      // 3. Fetch Real Posted Audit Logs from Content Branch
      const cBranch = auth.contentBranch || 'content';
      let realPosted = [];
      let totalMediaBytes = 0;

      // Try posted_twitch_log.json on content branch, fallback to master
      for (const branchAttempt of [cBranch, pBranch]) {
        try {
          const logRes = await fetch(`https://api.github.com/repos/${auth.repo}/contents/posted_twitch_log.json?ref=${branchAttempt}`, { headers });
          if (logRes.ok) {
            const logData = await logRes.json();
            const logStr = decodeURIComponent(escape(atob(logData.content)));
            const logEntries = JSON.parse(logStr);
            if (Array.isArray(logEntries)) {
              logEntries.forEach((entry, idx) => {
                const uploads = entry.uploads || {};
                const clips = entry.clips_used || [];
                const clipMap = entry.upload_clip_map || {};
                const captionsMap = entry.upload_captions || {};

                for (const [k, v] of Object.entries(uploads)) {
                  if (typeof v === 'string' && !v.toLowerCase().startsWith('failed')) {
                    const isIg1 = k.includes('instagram_1');
                    const isIg2 = k.includes('instagram_2') || (!isIg1 && k.includes('instagram'));
                    const isYt = k.includes('youtube');

                    let cname = 'Published Clip';
                    if (clipMap[k]) {
                      cname = clipMap[k];
                    } else if (clips.length === 1) {
                      cname = clips[0];
                    } else if (clips.length > 1) {
                      if (isYt) {
                        cname = clips[0];
                      } else if (isIg1 || isIg2) {
                        cname = clips[1] || clips[0];
                      }
                    }

                    const cleanTitle = cname.replace('.mp4', '').replace(/^\d{4}-\d{2}-\d{2}-/, '').replace(/_/g, ' ');

                    realPosted.push({
                      id: `posted_${idx}_${k}`,
                      title: cleanTitle.charAt(0).toUpperCase() + cleanTitle.slice(1),
                      caption: captionsMap[k] || '',
                      account: isIg1 ? 'ig1' : isIg2 ? 'ig2' : 'youtube',
                      platform: isIg1 ? 'Instagram (@solvikz)' : isIg2 ? 'Instagram (@loopablez)' : 'YouTube Shorts',
                      date: entry.timestamp,
                      timestamp: entry.timestamp,
                      url: v,
                      status: 'posted',
                      cname: cname
                    });
                  }
                }
              });
            }
            if (realPosted.length > 0) break;
          }
        } catch (e) {
          console.warn('posted_twitch_log read attempt error:', e);
        }
      }

      // 4. Fetch Real Staged Pipeline Clips from Content Branch
      let realPipeline = [];
      const pipelineCandidates = [
        'output/stream_pipeline',
        'output/twitch_pipeline'
      ];

      for (const folder of pipelineCandidates) {
        try {
          const folderRes = await fetch(`https://api.github.com/repos/${auth.repo}/contents/${folder}?ref=${cBranch}`, { headers });
          if (folderRes.ok) {
            const files = await folderRes.json();
            if (Array.isArray(files)) {
              const mp4s = files.filter(f => f.name.endsWith('.mp4'));
              const jsons = files.filter(f => f.name.endsWith('.json'));

              for (const mp4 of mp4s) {
                totalMediaBytes += (mp4.size || 0);
                const baseName = mp4.name.replace('.mp4', '');
                const jsonFile = jsons.find(j => j.name === `${baseName}.json`);

                let meta = {
                  title: baseName.replace(/^\d{4}-\d{2}-\d{2}-/, '').replace(/_/g, ' '),
                  caption: `#gaming #shorts #reels`,
                  streamer: 'Streamer',
                  z_score: 3.2,
                  hype_score: 150
                };

                let jsonSha = null;
                if (jsonFile) {
                  totalMediaBytes += (jsonFile.size || 0);
                  jsonSha = jsonFile.sha;
                  try {
                    const mRes = await fetch(jsonFile.url, { headers });
                    if (mRes.ok) {
                      const mData = await mRes.json();
                      const mStr = decodeURIComponent(escape(atob(mData.content)));
                      const parsedMeta = JSON.parse(mStr);
                      meta = { ...meta, ...parsedMeta };
                    }
                  } catch (e) {
                    console.warn('Metadata fetch error for', jsonFile.name, e);
                  }
                }

                // Raw GitHub URL for video playback
                const rawVideoUrl = mp4.download_url || `https://raw.githubusercontent.com/${auth.repo}/${cBranch}/${mp4.path}`;

                const isTrial = Boolean(
                  meta.trial ||
                  meta.is_trial ||
                  meta.post_kind === 'trial' ||
                  (meta.target && meta.target.toLowerCase().includes('trial'))
                );

                const durSec = meta.duration_sec || 35;
                const durMinStr = `${Math.floor(durSec / 60)}:${String(durSec % 60).padStart(2, '0')}`;

                let assignedAcc = 'ig1';
                if (meta.account) {
                  assignedAcc = meta.account === 'yt' ? 'youtube' : meta.account;
                } else if (meta.target) {
                  const tLower = meta.target.toLowerCase();
                  if (tLower.includes('loopablez') || tLower.includes('slot 2')) assignedAcc = 'ig2';
                  else if (tLower.includes('solvikz') || tLower.includes('slot 1')) assignedAcc = 'ig1';
                  else if (tLower.includes('youtube') || tLower.includes('shorts')) assignedAcc = 'youtube';
                }

                realPipeline.push({
                  id: `real_${baseName}`,
                  filename: mp4.name,
                  streamer: meta.streamer || meta.username || 'Stream Highlight',
                  title: meta.title || baseName.replace(/_/g, ' '),
                  caption: meta.caption || `${meta.title} #gaming #reels`,
                  duration: durMinStr,
                  durationSec: durSec,
                  sigma: meta.z_score ? `${Number(meta.z_score).toFixed(1)} σ` : '3.2 σ',
                  motion: 'Active Motion Detected',
                  layout: meta.layout || 'Dual Stack 9:16',
                  target: meta.target || (meta.post_to_yt ? 'Instagram & YouTube' : 'Instagram Only'),
                  post_to_yt: Boolean(meta.post_to_yt || (meta.target && meta.target.toLowerCase().includes('youtube'))),
                  posted_to_instagram: Boolean(meta.posted_to_instagram),
                  posted_to_youtube: Boolean(meta.posted_to_youtube),
                  account: assignedAcc,
                  isTrial: isTrial,
                  status: 'staged',
                  approval_status: meta.approval_status || meta.status || 'pending',
                  timestamp: meta.timestamp || meta.staged_at || meta.created_at || null,
                  videoUrl: rawVideoUrl,
                  path: mp4.path,
                  sha: mp4.sha,
                  jsonPath: jsonFile ? jsonFile.path : null,
                  jsonSha: jsonSha
                });
              }
            }
          }
          if (realPipeline.length > 0) break;
        } catch (e) {
          console.warn('Pipeline folder fetch error for', folder, e);
        }
      }

      // 5. Query Posted Archive Folders for Real Storage Size
      const postedCandidates = ['output/stream_posted', 'output/twitch_posted'];
      for (const pFolder of postedCandidates) {
        try {
          const pRes = await fetch(`https://api.github.com/repos/${auth.repo}/contents/${pFolder}?ref=${cBranch}`, { headers });
          if (pRes.ok) {
            const pFiles = await pRes.json();
            if (Array.isArray(pFiles)) {
              pFiles.forEach(f => { totalMediaBytes += (f.size || 0); });
            }
          }
        } catch (e) {}
      }

      // Sort realPipeline: Approved first, pending second, denied last.
      // Within each status, sort chronologically by date/timestamp (FIFO, never alphabetically).
      realPipeline.sort((a, b) => {
        const getPrio = (c) => (c.approval_status === 'approved' ? 0 : c.approval_status === 'denied' ? 2 : 1);
        const prioA = getPrio(a);
        const prioB = getPrio(b);
        if (prioA !== prioB) return prioA - prioB;

        const getTs = (c) => {
          if (c.timestamp) {
            const t = new Date(c.timestamp).getTime();
            if (!isNaN(t)) return t;
          }
          const m = (c.filename || '').match(/^(\d{4}-\d{2}-\d{2})/);
          if (m) {
            const t = new Date(m[1]).getTime();
            if (!isNaN(t)) return t;
          }
          return 0;
        };
        return getTs(a) - getTs(b);
      });

      // 6. Bind Real Data to Dashboard State (DO NOT Fallback to Fake Demo Data)
      pipelineClips = realPipeline;
      postedClips = realPosted;

      // Update real top stats from actual posted data (matching local/UTC day or rolling 24h window)
      const now = new Date();
      const isRecentPost = (p) => {
        const raw = p.timestamp || p.date;
        if (!raw) return false;
        const d = new Date(raw);
        const t = d.getTime();
        if (isNaN(t)) return false;
        const sameLocalDay = d.toDateString() === now.toDateString();
        const sameUtcDay = d.toISOString().split('T')[0] === now.toISOString().split('T')[0];
        const within24h = (now.getTime() - t) >= 0 && (now.getTime() - t) <= 24 * 3600 * 1000;
        return sameLocalDay || sameUtcDay || within24h;
      };

      const recentPosted = realPosted.filter(isRecentPost);

      const ig1Count = recentPosted.filter(p => p.account === 'ig1').length;
      const ig2Count = recentPosted.filter(p => p.account === 'ig2').length;
      const ytCount = recentPosted.filter(p => p.account === 'youtube').length;

      const totalMb = (totalMediaBytes / (1024 * 1024)).toFixed(1);
      const storagePct = ((totalMediaBytes / (1500 * 1024 * 1024)) * 100).toFixed(1);

      const ig1ValEl = document.getElementById('ig1-stat-val');
      const ig2ValEl = document.getElementById('ig2-stat-val');
      const ytValEl = document.getElementById('yt-stat-val');
      const storageValEl = document.getElementById('storage-stat-val');
      const storageDescEl = document.getElementById('storage-stat-desc');

      if (ig1ValEl) ig1ValEl.innerHTML = `${ig1Count} / ${settings.ig1Posts} <small class="text-dim-unit">in 24h</small>`;
      if (ig2ValEl) ig2ValEl.innerHTML = `${ig2Count} / ${settings.ig2Posts} <small class="text-dim-unit">in 24h</small>`;
      if (ytValEl) ytValEl.innerHTML = `${ytCount} / ${settings.ytPosts} <small class="text-dim-unit">in 24h</small>`;
      if (storageValEl) storageValEl.innerHTML = `${totalMb} MB <small class="text-dim-unit">/ 1500 MB</small>`;
      if (storageDescEl) storageDescEl.innerText = `${storagePct}% used • Archive retained for 7 days`;

      // Update Live Cooldown Timers from exact ISO timestamps
      updateCooldownDisplays();

      // Update Calendar & Queue with real GitHub data
      calculateDynamicSpacing();
      renderCalendar();
      renderPipelineQueue();

      if (dot) dot.className = 'dot online';
      if (statusText) statusText.innerText = `Connected: ${auth.repo} (${pipelineClips.length} in queue, ${postedClips.length} posted)`;
    } catch (err) {
      console.error('GitHub API Sync Error:', err);
      if (dot) dot.className = 'dot danger';
      if (statusText) statusText.innerText = `Auth Error: ${err.message || 'Check Token'}`;
      alert(`GitHub Sync Failed: ${err.message || 'Could not connect'}\n\nPlease verify that your token has 'repo' and 'workflow' scopes.`);
    }
  }

  function updateTrialDesc() {
    const descEl = document.getElementById('desc-ig1-trial');
    if (descEl) {
      const total = settings.ig1Posts || 3;
      const trial = typeof settings.ig1TrialPosts !== 'undefined' ? settings.ig1TrialPosts : 2;
      const reg = Math.max(0, total - trial);
      descEl.innerText = `${trial} of ${total} posts will test with non-followers (${reg} standard reel${reg === 1 ? '' : 's'})`;
    }
  }

  function updateCooldownDisplays() {
    const now = new Date();

    let lastIg1Ts = null;
    let lastIg2Ts = null;
    let lastYtTs = null;

    postedClips.forEach(p => {
      const rawDate = p.timestamp || p.date;
      if (!rawDate) return;
      const t = new Date(rawDate).getTime();
      if (isNaN(t)) return;

      if (p.account === 'ig1') {
        if (!lastIg1Ts || t > lastIg1Ts) lastIg1Ts = t;
      } else if (p.account === 'ig2') {
        if (!lastIg2Ts || t > lastIg2Ts) lastIg2Ts = t;
      } else if (p.account === 'youtube') {
        if (!lastYtTs || t > lastYtTs) lastYtTs = t;
      }
    });

    // Dynamic Interval Formula: (24h / posts_per_day) - 30m buffer
    function getAccountIntervalMinutes(postsPerDay) {
      const n = parseInt(postsPerDay, 10);
      if (!n || n <= 0) return Infinity;
      return Math.max(15, Math.round((24 * 60 / n) - 30));
    }

    const ig1MinGap = getAccountIntervalMinutes(settings.ig1Posts || 3);
    const ig2MinGap = getAccountIntervalMinutes(settings.ig2Posts || 3);
    const ytMinGap = getAccountIntervalMinutes(settings.ytPosts || 3);

    function computeDesc(lastTs, gapMinutes, prefix = '') {
      if (!lastTs) {
        return { text: prefix ? `${prefix} • Cooldown: Ready` : 'Cooldown: Ready', isReady: true };
      }
      const elapsedMinutes = Math.floor((now.getTime() - lastTs) / (1000 * 60));
      if (elapsedMinutes < 0 || elapsedMinutes >= gapMinutes) {
        const agoStr = elapsedMinutes < 60 ? `${Math.max(0, elapsedMinutes)}m ago` : `${Math.floor(elapsedMinutes / 60)}h ${elapsedMinutes % 60}m ago`;
        return { text: prefix ? `${prefix} • Ready (Last: ${agoStr})` : `Cooldown: Ready (Last: ${agoStr})`, isReady: true };
      }
      const remMinutes = Math.max(1, Math.ceil(gapMinutes - elapsedMinutes));
      const remH = Math.floor(remMinutes / 60);
      const remM = remMinutes % 60;
      const remStr = remH > 0 ? `${remH}h ${remM}m` : `${remM}m`;
      const agoStr = elapsedMinutes < 60 ? `${elapsedMinutes}m ago` : `${Math.floor(elapsedMinutes / 60)}h ${elapsedMinutes % 60}m ago`;
      return { text: `Posted ${agoStr} • Cooldown: ${remStr} remaining`, isReady: false };
    }

    const ig1DescEl = document.getElementById('ig1-stat-desc');
    const ig2DescEl = document.getElementById('ig2-stat-desc');
    const ytDescEl = document.getElementById('yt-stat-desc');

    if (ig1DescEl) {
      const trial = typeof settings.ig1TrialPosts !== 'undefined' ? settings.ig1TrialPosts : 1;
      const prefix = trial > 0 ? 'Trial Eligible' : 'Regular Reels';
      const info = computeDesc(lastIg1Ts, ig1MinGap, prefix);
      ig1DescEl.innerText = info.text;
      if (info.isReady) ig1DescEl.classList.add('highlight');
      else ig1DescEl.classList.remove('highlight');
    }

    if (ig2DescEl) {
      const info = computeDesc(lastIg2Ts, ig2MinGap, 'Regular Reels');
      ig2DescEl.innerText = info.text;
      if (info.isReady) ig2DescEl.classList.add('highlight');
      else ig2DescEl.classList.remove('highlight');
    }

    if (ytDescEl) {
      const info = computeDesc(lastYtTs, ytMinGap, 'YouTube Shorts');
      ytDescEl.innerText = info.text;
      if (info.isReady) ytDescEl.classList.add('highlight');
      else ytDescEl.classList.remove('highlight');
    }
  }

  function applyRemoteConfig(cfg) {
    const sched = cfg.publishing_schedule || {};
    const igAccounts = sched.instagram_accounts || [];

    const ig1 = igAccounts.find(a => a.slot === 1);
    if (ig1) {
      const reg = ig1.regular_per_day || 0;
      const trial = ig1.trial_per_day || 0;
      settings.ig1Posts = reg + trial;
      settings.ig1TrialPosts = trial;

      const s1 = document.getElementById('slider-ig1');
      const v1 = document.getElementById('val-ig1');
      if (s1) s1.value = settings.ig1Posts;
      if (v1) v1.innerText = settings.ig1Posts;

      const s1Trial = document.getElementById('slider-ig1-trial');
      const v1Trial = document.getElementById('val-ig1-trial');
      if (s1Trial) {
        s1Trial.max = settings.ig1Posts;
        s1Trial.value = settings.ig1TrialPosts;
      }
      if (v1Trial) v1Trial.innerText = settings.ig1TrialPosts;
      updateTrialDesc();
    }

    const ig2 = igAccounts.find(a => a.slot === 2);
    if (ig2) {
      settings.ig2Posts = ig2.regular_per_day || 3;
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
        const branch = (document.getElementById('setup-branch')?.value || 'master').trim();
        const contentBranch = (document.getElementById('setup-content-branch')?.value || 'content').trim();

        if (!pat) {
          alert('Please enter a GitHub Personal Access Token or choose Explore with Demo Data.');
          return;
        }

        auth = { pat, repo, branch, contentBranch, isDemo: false };
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
        if (selectedClip) approveClip(selectedClip, true);
      });
    }

    const btnDenyClip = document.getElementById('btn-deny-clip');
    if (btnDenyClip) {
      btnDenyClip.addEventListener('click', () => {
        if (selectedClip) denyClip(selectedClip);
      });
    }

    const btnDeleteClip = document.getElementById('btn-delete-clip');
    if (btnDeleteClip) {
      btnDeleteClip.addEventListener('click', () => {
        if (selectedClip) deleteClip(selectedClip);
      });
    }

    // Start Real-Time Current Time Indicator Loop
    setInterval(updateCurrentTimeIndicator, 30000);

    // 7. Settings Sliders
    const bindSlider = (id, valId, key, suffix = '') => {
      const el = document.getElementById(id);
      const valEl = document.getElementById(valId);
      if (!el || !valEl) return;

      if (typeof settings[key] !== 'undefined') {
        el.value = settings[key];
        valEl.innerText = `${settings[key]}${suffix}`;
      }

      el.addEventListener('input', () => {
        valEl.innerText = `${el.value}${suffix}`;
        settings[key] = parseInt(el.value, 10);
        safeSetStorage(STORAGE_KEY_SETTINGS, settings);
        calculateDynamicSpacing();
        renderCalendar();
        renderPipelineQueue();
      });
    };

    // Specialized Slider for Instagram 1 and Dynamic Trial Allocation
    const sliderIg1 = document.getElementById('slider-ig1');
    const valIg1 = document.getElementById('val-ig1');
    const sliderIg1Trial = document.getElementById('slider-ig1-trial');
    const valIg1Trial = document.getElementById('val-ig1-trial');

    if (sliderIg1) {
      sliderIg1.value = settings.ig1Posts || 3;
      if (valIg1) valIg1.innerText = settings.ig1Posts || 3;

      sliderIg1.addEventListener('input', () => {
        const total = parseInt(sliderIg1.value, 10);
        if (valIg1) valIg1.innerText = total;
        settings.ig1Posts = total;

        // Dynamically clamp Trial Reels Share between 0 and total posts
        if (sliderIg1Trial) {
          sliderIg1Trial.max = total;
          if (settings.ig1TrialPosts > total) {
            settings.ig1TrialPosts = total;
            sliderIg1Trial.value = total;
            if (valIg1Trial) valIg1Trial.innerText = total;
          }
        }
        updateTrialDesc();
        safeSetStorage(STORAGE_KEY_SETTINGS, settings);
        calculateDynamicSpacing();
        renderCalendar();
        renderPipelineQueue();
      });
    }

    if (sliderIg1Trial) {
      sliderIg1Trial.max = settings.ig1Posts || 3;
      sliderIg1Trial.value = settings.ig1TrialPosts || 2;
      if (valIg1Trial) valIg1Trial.innerText = sliderIg1Trial.value;
      updateTrialDesc();

      sliderIg1Trial.addEventListener('input', () => {
        const trial = parseInt(sliderIg1Trial.value, 10);
        if (valIg1Trial) valIg1Trial.innerText = trial;
        settings.ig1TrialPosts = trial;
        updateTrialDesc();
        safeSetStorage(STORAGE_KEY_SETTINGS, settings);
        calculateDynamicSpacing();
        renderCalendar();
        renderPipelineQueue();
      });
    }

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

        if (sliderIg1Trial) {
          sliderIg1Trial.max = settings.ig1Posts;
          if (settings.ig1TrialPosts > settings.ig1Posts) {
            settings.ig1TrialPosts = settings.ig1Posts;
            sliderIg1Trial.value = settings.ig1Posts;
            if (valIg1Trial) valIg1Trial.innerText = settings.ig1Posts;
          }
        }
        updateTrialDesc();

        safeSetStorage(STORAGE_KEY_SETTINGS, settings);
        calculateDynamicSpacing();
        renderCalendar();
      });
    }

    // 9. Save Settings Button
    const btnSaveSettings = document.getElementById('btn-save-settings');
    if (btnSaveSettings) {
      btnSaveSettings.addEventListener('click', async () => {
        safeSetStorage(STORAGE_KEY_SETTINGS, settings);

        if (auth.pat && !auth.isDemo) {
          try {
            btnSaveSettings.innerText = 'Saving to GitHub...';
            const headers = {
              'Authorization': `token ${auth.pat.trim()}`,
              'Accept': 'application/vnd.github.v3+json'
            };
            const pBranch = auth.branch || 'master';

            // 1. Get current config.json to get sha and existing structure
            const curRes = await fetch(`https://api.github.com/repos/${auth.repo}/contents/config.json?ref=${pBranch}`, { headers });
            if (curRes.ok) {
              const curData = await curRes.json();
              const curStr = decodeURIComponent(escape(atob(curData.content)));
              const cfg = JSON.parse(curStr);

              // Update config
              if (!cfg.publishing_schedule) cfg.publishing_schedule = {};
              if (!cfg.publishing_schedule.youtube) cfg.publishing_schedule.youtube = {};
              cfg.publishing_schedule.youtube.shorts_per_day = settings.ytPosts;

              if (Array.isArray(cfg.publishing_schedule.instagram_accounts)) {
                const acc1 = cfg.publishing_schedule.instagram_accounts.find(a => a.slot === 1);
                if (acc1) {
                  acc1.trial_per_day = settings.ig1TrialPosts;
                  acc1.regular_per_day = Math.max(0, settings.ig1Posts - settings.ig1TrialPosts);
                  acc1.hard_daily_ceiling = Math.max(acc1.hard_daily_ceiling || 4, settings.ig1Posts);
                }
                const acc2 = cfg.publishing_schedule.instagram_accounts.find(a => a.slot === 2);
                if (acc2) {
                  acc2.regular_per_day = settings.ig2Posts;
                  acc2.trial_per_day = 0;
                  acc2.hard_daily_ceiling = Math.max(acc2.hard_daily_ceiling || 4, settings.ig2Posts);
                }
              }

              const updatedJsonStr = JSON.stringify(cfg, null, 2);
              const b64 = btoa(unescape(encodeURIComponent(updatedJsonStr)));

              // Commit updated config.json to GitHub
              const putRes = await fetch(`https://api.github.com/repos/${auth.repo}/contents/config.json`, {
                method: 'PUT',
                headers,
                body: JSON.stringify({
                  message: 'chore(config): update posting schedule & trial reels share via dashboard',
                  content: b64,
                  sha: curData.sha,
                  branch: pBranch
                })
              });

              if (putRes.ok) {
                alert('Settings saved and committed to GitHub repository (config.json)!');
              } else {
                alert('Settings saved locally in dashboard.');
              }
            }
          } catch (e) {
            console.warn('Failed to commit config to GitHub:', e);
            alert('Settings saved locally in dashboard.');
          } finally {
            btnSaveSettings.innerHTML = '<svg class="icon" viewBox="0 0 24 24"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg> Save Settings to Repository';
          }
        } else {
          alert('Settings saved. Future scheduled slots adjusted. Staged pipeline clips preserved.');
        }
      });
    }

    // 10. Diagnostics and Action Triggers
    const btnSync = document.getElementById('btn-sync');
    if (btnSync) btnSync.addEventListener('click', syncWithGitHub);

    // Generic helper to dispatch GitHub Actions workflows via GitHub API
    async function triggerGitHubWorkflow(workflowFile, inputs = {}) {
      if (!auth.pat || auth.isDemo) {
        alert('GitHub Personal Access Token required.\n\nPlease open Setup and enter a PAT with "repo" and "workflow" scopes.');
        return false;
      }
      const repo = auth.repo || 'Deeptanil/HyperClip-AI';
      const branch = auth.branch || 'master';
      const headers = {
        'Authorization': `token ${auth.pat.trim()}`,
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json'
      };
      const res = await fetch(`https://api.github.com/repos/${repo}/actions/workflows/${workflowFile}/dispatches`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          ref: branch,
          inputs: inputs
        })
      });
      if (res.status === 204 || res.ok) {
        return true;
      }
      const err = await res.json().catch(() => ({}));
      throw new Error(err.message || `HTTP ${res.status}`);
    }

    const btnRunAction = document.getElementById('btn-run-action');
    if (btnRunAction) {
      btnRunAction.addEventListener('click', async () => {
        const origHtml = btnRunAction.innerHTML;
        btnRunAction.disabled = true;
        btnRunAction.innerHTML = `<span>Starting...</span>`;
        try {
          await triggerGitHubWorkflow('twitch_clipper.yml', { force: 'false' });
          btnRunAction.innerHTML = `<span>Dispatched!</span>`;
          alert('Successfully triggered Auto-Posting & Clipping cycle on GitHub Actions!\n\nThe runner is starting now. Click Sync in 1-2 minutes to see results.');
          setTimeout(() => syncWithGitHub(), 15000);
        } catch (err) {
          console.error('Failed to trigger workflow:', err);
          alert(`Failed to trigger GitHub Actions workflow: ${err.message}\n\nPlease verify that your PAT in Setup has the "workflow" scope enabled.`);
        } finally {
          setTimeout(() => {
            btnRunAction.disabled = false;
            btnRunAction.innerHTML = origHtml;
          }, 3000);
        }
      });
    }

    const btnHarvestFresh = document.getElementById('btn-harvest-fresh');
    if (btnHarvestFresh) {
      btnHarvestFresh.addEventListener('click', async () => {
        const origHtml = btnHarvestFresh.innerHTML;
        btnHarvestFresh.disabled = true;
        btnHarvestFresh.innerHTML = `<span>Scanning...</span>`;
        try {
          await triggerGitHubWorkflow('twitch_clipper.yml', { harvest_only: 'true' });
          btnHarvestFresh.innerHTML = `<span>Started!</span>`;
          alert('Successfully dispatched Live Stream Scanner on GitHub Actions!\n\nIt is harvesting live Twitch clips and staging them into the pipeline.');
          setTimeout(() => syncWithGitHub(), 30000);
        } catch (err) {
          console.error('Failed to dispatch stream scanner:', err);
          alert(`Failed to trigger stream scanner: ${err.message}\n\nPlease verify that your PAT in Setup has the "workflow" scope enabled.`);
        } finally {
          setTimeout(() => {
            btnHarvestFresh.disabled = false;
            btnHarvestFresh.innerHTML = origHtml;
          }, 3000);
        }
      });
    }

    const btnTestDiag = document.getElementById('btn-test-diag');
    if (btnTestDiag) {
      btnTestDiag.addEventListener('click', async () => {
        const origHtml = btnTestDiag.innerHTML;
        btnTestDiag.disabled = true;
        btnTestDiag.innerHTML = `<span>Testing...</span>`;
        try {
          if (!auth.pat || auth.isDemo) {
            alert('Demo Mode: Enter your GitHub PAT in Setup to test live credentials.');
            return;
          }
          const headers = {
            'Authorization': `token ${auth.pat.trim()}`,
            'Accept': 'application/vnd.github.v3+json'
          };
          const repoRes = await fetch(`https://api.github.com/repos/${auth.repo}`, { headers });
          if (!repoRes.ok) throw new Error(`GitHub token error: ${repoRes.statusText}`);
          const repoData = await repoRes.json();
          alert(`GitHub Connected Successfully!\n\nRepository: ${repoData.full_name}\nDefault Branch: ${repoData.default_branch}\nPermissions: Push=${repoData.permissions?.push || false}, Admin=${repoData.permissions?.admin || false}\n\nAccounts @solvikz, @loopablez, and YouTube credentials are stored securely in GitHub Repository Secrets.`);
        } catch (err) {
          alert(`Credential Diagnostic Failed: ${err.message}`);
        } finally {
          btnTestDiag.disabled = false;
          btnTestDiag.innerHTML = origHtml;
        }
      });
    }
  }

  // --- Initial Startup Execution (Race-Condition Free) ---
  function startApp() {
    initUI();
    if (!auth.pat || auth.isDemo) {
      loadDemoData();
    } else {
      syncWithGitHub();
    }
    // Live real-time cooldown countdown ticker
    setInterval(updateCooldownDisplays, 30000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startApp);
  } else {
    startApp();
  }

})();
