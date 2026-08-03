(() => {
  "use strict";

  const doc = document;

  function exposeJsonScript(id, dataAttribute, fallback) {
    const node = doc.getElementById(id);
    if (!node) {
      return null;
    }

    try {
      const decoded = JSON.parse(node.textContent || JSON.stringify(fallback));
      if (typeof decoded === "string") {
        // Current Django views pass pre-serialized JSON. Validate the inner value,
        // then expose it to the existing app.js consumers without using HTML parsing.
        JSON.parse(decoded);
        node.textContent = decoded;
      } else {
        node.textContent = JSON.stringify(decoded);
      }
    } catch (_error) {
      node.textContent = JSON.stringify(fallback);
    }

    node.setAttribute(dataAttribute, "");
    return node;
  }

  const chatFeed = exposeJsonScript("chat-feed-json", "data-feed-json", []);
  const chatMembers = exposeJsonScript("chat-members-json", "data-members-json", []);
  const privateFeed = exposeJsonScript("private-feed-json", "data-feed-json", []);
  const privateMembers = exposeJsonScript("private-members-json", "data-members-json", []);
  const mailMembers = exposeJsonScript("mail-members-json", "data-members-json", []);
  exposeJsonScript("mail-envelope-json", "data-envelope-json", {});

  // Keep references alive for explicitness and easier browser debugging.
  void chatFeed;
  void chatMembers;
  void privateFeed;
  void privateMembers;

  if (!mailMembers) {
    return;
  }

  const root = mailMembers.closest("[data-e2ee-mail]");
  const box = root ? root.querySelector("[data-recipient-picks]") : null;
  if (!box) {
    return;
  }

  let people = [];
  try {
    people = JSON.parse(mailMembers.textContent || "[]");
  } catch (_error) {
    people = [];
  }

  const eligible = people.filter((person) => person && person.has_keys);
  box.replaceChildren();

  if (!eligible.length) {
    const empty = doc.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "Keine Kollegen mit Schlüsseln.";
    box.append(empty);
    return;
  }

  for (const person of eligible) {
    const label = doc.createElement("label");
    const input = doc.createElement("input");
    const text = doc.createElement("span");

    input.type = "checkbox";
    input.name = "recipient_ids";
    input.value = String(person.user_id);
    text.textContent = String(person.label || "Unbenanntes Konto");

    label.append(input, text);
    box.append(label);
  }
})();
