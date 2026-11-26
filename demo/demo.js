"use strict";

const main = document.querySelector("main");
let catalog;
let rendered = false;
let captureDate;
const labels = { person: "Person", car: "Car" };

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function link(href, text, className) {
  const a = node("a", className, text);
  a.href = href;
  return a;
}

function clock(seconds) {
  return new Date(Math.floor(seconds) * 1000).toISOString().slice(14, 19);
}

function heading(title, description) {
  document.title = `${title} · HeisenCam demo`;
  main.append(node("h1", "", title));
  if (description) main.append(node("p", "summary", description));
}

function card(href, poster, title, subtitle) {
  const a = link(href, undefined, "card");
  const frame = node("div", "frame");
  const img = node("img");
  img.src = poster;
  img.alt = "";
  img.decoding = "async";
  const play = node("span", "play", "▶");
  play.setAttribute("aria-hidden", "true");
  frame.append(img, play);
  const caption = node("div", "caption");
  caption.append(node("strong", "", title), node("small", "", subtitle));
  a.append(frame, caption);
  return a;
}

function grid(items) {
  const section = node("div", "grid");
  section.append(...items);
  return section;
}

function cameraFor(id) {
  return catalog.cameras.find(camera => camera.id === id);
}

function cameras() {
  heading("Cameras", "Six public traffic cameras in California and Calgary. Select a view to play its recorded sample.");
  main.append(grid(catalog.cameras.map(camera =>
    card(`#camera/${camera.id}`, `posters/${camera.id}.webp`, camera.name, camera.location)
  )));
}

function player(source, poster, title, startAt = 0, loop = false) {
  const video = node("video", "player");
  video.controls = true;
  video.muted = true;
  video.playsInline = true;
  video.loop = loop;
  video.preload = "metadata";
  video.poster = poster;
  video.setAttribute("aria-label", title);
  video.addEventListener("loadedmetadata", () => {
    if (!video.isConnected) return;
    if (startAt) video.currentTime = Math.min(startAt, video.duration);
    video.play().catch(() => { /* Playback is also available through native controls. */ });
  }, { once: true });
  video.src = source;
  main.append(video);
}

function eventCard(event) {
  const camera = cameraFor(event.camera);
  return card(`#event/${event.id}`, `events/${event.id}.webp`, `${labels[event.label]} · ${event.score}%`,
    `${camera.name} · ${clock(event.offset)}`);
}

function cameraView(camera) {
  main.append(link("#cameras", "← All cameras", "back"));
  heading(camera.name, `${camera.location} · ${camera.kind} · ${captureDate}`);
  player(`media/${camera.id}.mp4`, `posters/${camera.id}.webp`, camera.name, 0, true);
  main.append(node("p", "metadata", camera.kind === "Time-lapse"
    ? "Eight municipal camera stills, two seconds per image."
    : "A 16-second excerpt from the public traffic stream."));
  const related = catalog.events.filter(event => event.camera === camera.id);
  if (related.length) main.append(node("h2", "", "Detections in this sample"), grid(related.map(eventCard)));
}

function birdseye() {
  heading("Birdseye", "Play all six recorded views together.");
  player("birdseye.mp4", "posters/birdseye.webp", "Six-camera overview", 0, true);
  const links = node("div", "camera-links");
  links.append(...catalog.cameras.map(camera => link(`#camera/${camera.id}`, camera.name)));
  main.append(node("h2", "", "Open a camera"), links);
}

function filter(label, choices) {
  const wrap = node("div", "filter");
  const caption = node("label", "", label);
  const select = node("select");
  select.id = `filter-${label.toLowerCase()}`;
  caption.htmlFor = select.id;
  for (const [value, name] of choices) select.add(new Option(name, value));
  wrap.append(caption, select);
  return { wrap, select };
}

function events() {
  heading("Events", "Confirmed detections from the six-camera Docker example. Select a snapshot to play the matching moment.");
  const camera = filter("Camera", [["", "All cameras"], ...catalog.cameras.map(cam => [cam.id, cam.name])]);
  const object = filter("Object", [["", "All objects"], ...Object.entries(labels)]);
  const filters = node("div", "filters");
  filters.append(camera.wrap, object.wrap);
  const results = node("div");
  function update() {
    const matches = catalog.events.filter(event =>
      (!camera.select.value || camera.select.value === event.camera) &&
      (!object.select.value || object.select.value === event.label));
    results.replaceChildren(matches.length ? grid(matches.map(eventCard)) :
      node("p", "summary", "No selected detections match these filters."));
  }
  filters.addEventListener("change", update);
  main.append(filters, results);
  update();
}

function eventView(event) {
  const camera = cameraFor(event.camera);
  main.append(link("#events", "← All events", "back"));
  heading(`${labels[event.label]} · ${camera.name}`,
    `${event.score}% snapshot score · ${clock(event.offset)} into the sample · ${camera.location}`);
  player(`media/${camera.id}.mp4`, `events/${event.id}.webp`, `${labels[event.label]} on ${camera.name}`, event.offset);
  const links = node("p", "camera-links");
  links.append(link(`#camera/${camera.id}`, "Open camera"), link(`events/${event.id}.webp`, "Open marked snapshot"));
  main.append(links);
}

function sources() {
  heading("Camera sources", `The samples were captured on ${captureDate}. The demo plays local copies of the footage.`);
  for (const [id, publisher] of Object.entries(catalog.publishers)) {
    const section = node("section", "source");
    section.append(node("h2", "", publisher.name), node("p", "", publisher.credit));
    const refs = node("p");
    refs.append(link(publisher.catalog, "Camera catalog"), " · ", link(publisher.terms, "Terms of use"));
    const list = node("ul", "sources");
    for (const cam of catalog.cameras.filter(cam => cam.publisher === id)) {
      const item = node("li");
      item.append(link(`#camera/${cam.id}`, cam.name), ` · ${cam.sourceName} · `, link(cam.sourceUrl, "Publisher feed"));
      list.append(item);
    }
    section.append(refs, list);
    main.append(section);
  }
}

function render() {
  if (!catalog) return;
  const [route = "cameras", id] = location.hash.slice(1).split("/").filter(Boolean);
  const current = ({ camera: "cameras", event: "events" })[route] || route;
  for (const a of document.querySelectorAll("nav a")) {
    if (a.getAttribute("href") === `#${current}`) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  }
  main.querySelector("video")?.pause();
  main.replaceChildren();
  if (route === "camera" && cameraFor(id)) cameraView(cameraFor(id));
  else if (route === "event" && catalog.events.some(event => event.id === id))
    eventView(catalog.events.find(event => event.id === id));
  else if (route === "birdseye") birdseye();
  else if (route === "events") events();
  else if (route === "sources") sources();
  else if (route === "cameras" || route === "content") cameras();
  else {
    heading("View unavailable");
    main.append(link("#cameras", "Return to cameras"));
  }
  if (rendered) {
    main.focus({ preventScroll: true });
    window.scrollTo(0, 0);
  }
  rendered = true;
}

document.querySelector(".skip").addEventListener("click", event => {
  event.preventDefault();
  main.focus();
});
window.addEventListener("hashchange", render);
fetch("catalog.json")
  .then(response => {
    if (!response.ok) throw new Error("Catalog unavailable");
    return response.json();
  })
  .then(data => {
    catalog = data;
    captureDate = new Intl.DateTimeFormat("en-GB", { dateStyle: "long", timeZone: "UTC" })
      .format(new Date(catalog.captureDate + "T00:00:00Z"));
    render();
  })
  .catch(() => {
    main.replaceChildren(node("h1", "", "Camera wall unavailable"),
      node("p", "summary", "Reload the page to try again."), link("../docs/", "Open documentation"));
  });
