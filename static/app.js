let supabaseClient = null;
let currentUser = null;

const message = document.getElementById("message");
const materials = document.getElementById("materials");

async function initialize() {
  try {
    const response = await fetch("/config");
    const config = await response.json();

    if (!config.supabaseUrl || !config.supabaseKey) {
      message.textContent = "Supabase connection is not configured yet.";
      materials.textContent = "Connection not configured.";
      return;
    }

    supabaseClient = window.supabase.createClient(
      config.supabaseUrl,
      config.supabaseKey
    );

    const { data } = await supabaseClient.auth.getSession();
    currentUser = data.session?.user || null;

    message.textContent = currentUser
      ? "Logged in as " + currentUser.email
      : "Please log in or create an account.";

    await loadMaterials();
  } catch (error) {
    message.textContent = "Connection error: " + error.message;
  }
}

document.getElementById("signup").onclick = async () => {
  if (!supabaseClient) return alert("Connection not ready.");

  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;

  const { error } = await supabaseClient.auth.signUp({
    email,
    password
  });

  message.textContent = error
    ? error.message
    : "Account created. Check your email if confirmation is required.";
};

document.getElementById("login").onclick = async () => {
  if (!supabaseClient) return alert("Connection not ready.");

  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;

  const { data, error } = await supabaseClient.auth.signInWithPassword({
    email,
    password
  });

  if (error) {
    message.textContent = error.message;
    return;
  }

  currentUser = data.user;
  message.textContent = "Logged in as " + currentUser.email;
  await loadMaterials();
};

document.getElementById("logout").onclick = async () => {
  if (!supabaseClient) return;

  await supabaseClient.auth.signOut();
  currentUser = null;
  message.textContent = "Logged out.";
};

document.getElementById("upload").onclick = async () => {
  if (!supabaseClient) return alert("Connection not ready.");
  if (!currentUser) return alert("Please log in before uploading.");

  const file = document.getElementById("file").files[0];
  const branch = document.getElementById("branch").value;
  const year = document.getElementById("year").value.trim();
  const subject = document.getElementById("subject").value.trim();

  if (!file || !year || !subject) {
    return alert("Choose a file and enter year and subject.");
  }

  const safeName = file.name.replace(/[^a-zA-Z0-9.-]/g, "");
  const path = ${branch}/${year}/${subject}/${Date.now()}_${safeName};

  message.textContent = "Uploading...";

  const { error } = await supabaseClient.storage
    .from("engineering-materials")
    .upload(path, file);

  if (error) {
    message.textContent = "Upload failed: " + error.message;
    return;
  }

  message.textContent = "Upload successful!";
  await loadMaterials();
};

document.getElementById("refresh").onclick = loadMaterials;

async function loadMaterials() {
  if (!supabaseClient) return;

  materials.textContent = "Loading materials...";

  const { data, error } = await supabaseClient.storage
    .from("engineering-materials")
    .list("", { limit: 100 });

  if (error) {
    materials.textContent = "Could not load materials: " + error.message;
    return;
  }

  materials.innerHTML = "";

  if (!data || data.length === 0) {
    materials.textContent = "No materials uploaded yet.";
    return;
  }

  for (const item of data) {
    if (!item.name) continue;

    const folder = document.createElement("div");
    folder.className = "material";

    const title = document.createElement("strong");
    title.textContent = item.name;
    folder.appendChild(title);

    if (item.id) {
      const { data: urlData } = supabaseClient.storage
        .from("engineering-materials")
        .getPublicUrl(item.name);

      const link = document.createElement("a");
      link.href = urlData.publicUrl;
      link.textContent = " Download";
      link.target = "_blank";
      folder.appendChild(link);
    } else {
      folder.appendChild(document.createTextNode(" (folder)"));
    }

    materials.appendChild(folder);
  }
}

initialize();
