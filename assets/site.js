/* Shared by every page. Holds the site's sections, in one place, and draws the top menu.

   A page declares its menu as an empty element and says where it sits and what it is:
     <nav class="top" data-root="../" data-current="tasks"></nav>
   data-root    path from this page back to the site root
   data-current which section to highlight (a key from LAB.SECTIONS); leave it off on the home page

   To add a section or move one out of development, change LAB.SECTIONS: the menu and home page both read it. */
const LAB = {
  SECTIONS: [
    {key:"models",   name:"Models",   path:"models/deserved-to-win/", status:"live", what:"Models you can try, check and argue with, starting with whether a result was deserved."},
    {key:"tasks",    name:"Tasks",    path:"tasks/",    status:"live", what:"What I'm working on now and what's finished, read from my task tracker on GitHub."},
    {key:"credits",  name:"Credits",  path:"credits/",  status:"live", what:"Everyone whose work appears in the lab, with where you'll find it."},
    {key:"repos",    name:"Repos",    path:"repos/",    status:"dev",  what:"Open footy analytics projects to study, each credited to its creator."},
    {key:"library",  name:"Library",  path:"library/",  status:"dev",  what:"The articles, papers, tools and datasets I'm learning from."},
    {key:"training", name:"Training", path:"training/", status:"dev",  what:"Hands-on practice with footy data that runs in your browser."}
  ]
};

/* ---------- top menu ---------- */
document.addEventListener("DOMContentLoaded", () => {
  const nav = document.querySelector("nav.top[data-root]");
  if(!nav) return;
  const root = nav.dataset.root;
  const brand = `<svg viewBox="0 0 32 22" aria-hidden="true"><ellipse cx="16" cy="11" rx="15" ry="10" fill="none" stroke="currentColor" stroke-width="2.5"/><path d="M16 1v20M10 11h12" stroke="currentColor" stroke-width="2"/></svg>`;
  nav.innerHTML = `<div class="wrap"><a class="brand" href="${root || "./"}">${brand}AFL Lab</a><span class="sp"></span>` +
    LAB.SECTIONS.map(s => `<a class="lnk" href="${root}${s.path}"${s.key === nav.dataset.current ? ' aria-current="page"' : ""}>${s.name}</a>`).join("") + `</div>`;
});
