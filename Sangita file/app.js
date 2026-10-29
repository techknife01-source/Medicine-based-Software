const STORAGE_KEY = "homoeocare.frontend-demo.v1";
const DOCTORS = [
  { name: "Dr. Ananya Rao", specialty: "Classical homeopathy", experience: "12 years' experience", emoji: "🌿" },
  { name: "Dr. Meera Iyer", specialty: "Family wellness", experience: "9 years' experience", emoji: "🌼" },
  { name: "Dr. Dev Shah", specialty: "Everyday wellness", experience: "7 years' experience", emoji: "🍃" },
];
const state = { user: null, savedProfile: null, products: window.HOMOEO_PRODUCTS, categories: [], brands: [], wishlist: [], cart: [], appointments: [], panelMode: "cart", authMode: "login", toastTimer: null, pendingAppointment: false, pendingProductAction: null, doctors: DOCTORS, selectedSlot: "", slotRequestId: 0 };
state.categories = [...new Set(state.products.map((product) => product.category))].sort();
state.brands = [...new Set(state.products.map((product) => product.brand))].sort();
const $ = (selector) => document.querySelector(selector);
const money = (amount) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(amount);
const categoryEmojis = { "Mother Tinctures": "🌿", Dilutions: "🧴", Biochemic: "💊", Tablets: "💊", Drops: "💧", Syrups: "🍯", Ointments: "🌼", Combo: "🎁", Healthcare: "🌱" };
const productShape = (product) => {
  const category = product.category;
  const kind = category === "Biochemic" || category === "Tablets" ? "box " + (product.name.includes("Kali") ? "purple" : "blue")
    : category === "Drops" ? "drop" : category === "Syrups" ? "syrup"
    : category === "Ointments" ? "ointment" : category === "Combo" ? "combo"
    : category === "Healthcare" ? "healthcare" : category === "Dilutions" ? ""
    : product.name.includes("Arnica") ? "" : "jar";
  return `<div class="product-illustration ${kind}"><span>${escapeHtml(product.emoji)}</span><b>${escapeHtml(product.name.split(" ").slice(0, 2).join(" ").toUpperCase())}</b><small>${escapeHtml(product.product_type)}</small></div>`;
};
function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
}
function persistDemoState() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      user: state.user,
      savedProfile: state.savedProfile || state.user,
      cart: state.cart.map((item) => ({ id: item.id, quantity: item.quantity })),
      wishlist: state.wishlist,
      appointments: state.appointments,
    }));
  } catch {
    throw new Error("This browser could not save demo data. Check your browser storage settings.");
  }
}
function restoreDemoState() {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (!saved) return;
  let data;
  try {
    data = JSON.parse(saved);
  } catch {
    throw new Error("Saved demo data could not be read. Clear this site's browser storage and reload.");
  }
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    throw new Error("Saved demo data is invalid. Clear this site's browser storage and reload.");
  }
  state.user = data.user && typeof data.user === "object" ? data.user : null;
  state.savedProfile = data.savedProfile && typeof data.savedProfile === "object" ? data.savedProfile : state.user;
  state.wishlist = Array.isArray(data.wishlist) ? data.wishlist.filter(Number.isInteger) : [];
  state.cart = Array.isArray(data.cart) ? data.cart.flatMap((item) => {
    const product = state.products.find((candidate) => candidate.id === item.id);
    const quantity = Number(item.quantity);
    if (!product || !Number.isInteger(quantity) || quantity < 1 || quantity > product.stock) return [];
    return [{ ...product, quantity, line_total: Math.round(product.discounted_price * quantity * 100) / 100 }];
  }) : [];
  state.appointments = Array.isArray(data.appointments) ? data.appointments : [];
}
async function demoRequest(url, options = {}) {
  const [path, query = ""] = url.split("?", 2);
  const params = new URLSearchParams(query);
  const method = options.method || "GET";
  let body = {};
  if (options.body) {
    try { body = JSON.parse(options.body); }
    catch { throw new Error("That demo action could not be completed."); }
  }
  const requireUser = () => {
    if (!state.user) throw new Error("Sign in to continue.");
    return state.user;
  };
  const findProduct = (id) => state.products.find((product) => product.id === Number(id));
  const save = () => persistDemoState();

  if (method === "GET" && path === "/demo/products") {
    const search = (params.get("search") || "").trim().toLowerCase();
    const category = params.get("category") || "All";
    const brand = params.get("brand") || "All";
    const maxPrice = Number(params.get("maxPrice")) || Infinity;
    const rating = Number(params.get("rating")) || 0;
    const inStock = params.get("available") === "true";
    const sort = params.get("sort") || "featured";
    const products = window.HOMOEO_PRODUCTS.filter((product) =>
      (!search || [product.name, product.brand, product.category, product.product_type].some((value) => value.toLowerCase().includes(search))) &&
      (category === "All" || product.category === category) &&
      (brand === "All" || product.brand === brand) &&
      (product.discounted_price <= maxPrice) &&
      (product.rating >= rating) &&
      (!inStock || product.stock > 0)
    );
    const sorters = {
      "price-low": (a, b) => a.discounted_price - b.discounted_price,
      "price-high": (a, b) => b.discounted_price - a.discounted_price,
      rating: (a, b) => b.rating - a.rating || b.review_count - a.review_count,
      newest: (a, b) => b.id - a.id,
      featured: (a, b) => b.rating - a.rating || b.review_count - a.review_count,
    };
    products.sort(sorters[sort] || sorters.featured);
    return { products, categories: state.categories, brands: state.brands, count: products.length };
  }
  if (method === "GET" && path === "/demo/me") return { user: state.user };
  if (method === "POST" && path === "/demo/register") {
    const name = String(body.name || "").trim();
    const email = String(body.email || "").trim().toLowerCase();
    const mobile = String(body.mobile || "").trim();
    if (name.length < 2 || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email) || mobile.replace(/\D/g, "").length < 10) {
      throw new Error("Please enter a name, valid email, and mobile number.");
    }
    state.user = { id: "local", name, email, mobile, address: "" };
    state.savedProfile = state.user;
    save();
    return { user: state.user };
  }
  if (method === "POST" && path === "/demo/login") {
    const email = String(body.email || "").trim().toLowerCase();
    if (!email || !String(body.password || "")) throw new Error("Enter an email and password to continue.");
    state.user = email === "hello@homoeocare.local"
      ? { id: "demo", name: "Demo Customer", email, mobile: "9876543210", address: "12 Garden Lane, Bengaluru" }
      : state.savedProfile?.email === email
        ? state.savedProfile
        : { id: "local", name: email.split("@")[0].replace(/[._-]/g, " "), email, mobile: "", address: "" };
    state.savedProfile = state.user;
    save();
    return { user: state.user };
  }
  if (method === "POST" && path === "/demo/logout") {
    state.user = null;
    save();
    return { ok: true };
  }
  if (method === "PATCH" && path === "/demo/profile") {
    requireUser();
    state.user = { ...state.user, name: String(body.name || "").trim(), mobile: String(body.mobile || "").trim(), address: String(body.address || "").trim() };
    state.savedProfile = state.user;
    save();
    return { user: state.user };
  }
  if (method === "GET" && path === "/demo/cart") {
    requireUser();
    return { items: state.cart, subtotal: state.cart.reduce((sum, item) => sum + item.line_total, 0) };
  }
  if (method === "POST" && path === "/demo/cart") {
    requireUser();
    const product = findProduct(body.productId);
    if (!product) throw new Error("That product is no longer available.");
    const existing = state.cart.find((item) => item.id === product.id);
    const quantity = (existing?.quantity || 0) + Math.max(1, Number(body.quantity) || 1);
    if (quantity > product.stock) throw new Error("There isn't enough stock for that quantity.");
    const item = { ...product, quantity, line_total: Math.round(product.discounted_price * quantity * 100) / 100 };
    state.cart = [...state.cart.filter((entry) => entry.id !== product.id), item];
    save();
    return { ok: true, count: state.cart.reduce((sum, entry) => sum + entry.quantity, 0) };
  }
  const cartMatch = path.match(/^\/demo\/cart\/(\d+)$/);
  if (cartMatch && method === "PATCH") {
    requireUser();
    const product = findProduct(cartMatch[1]);
    const quantity = Number(body.quantity);
    if (!product || !Number.isInteger(quantity) || quantity < 1 || quantity > product.stock) throw new Error("Choose an available quantity.");
    state.cart = state.cart.map((item) => item.id === product.id ? { ...product, quantity, line_total: Math.round(product.discounted_price * quantity * 100) / 100 } : item);
    save();
    return { ok: true };
  }
  if (cartMatch && method === "DELETE") {
    requireUser();
    state.cart = state.cart.filter((item) => item.id !== Number(cartMatch[1]));
    save();
    return { ok: true };
  }
  if (method === "GET" && path === "/demo/wishlist") {
    requireUser();
    return { items: window.HOMOEO_PRODUCTS.filter((product) => state.wishlist.includes(product.id)) };
  }
  if (method === "POST" && path === "/demo/wishlist") {
    requireUser();
    const product = findProduct(body.productId);
    if (!product) throw new Error("That product is no longer available.");
    const saved = !state.wishlist.includes(product.id);
    state.wishlist = saved ? [...state.wishlist, product.id] : state.wishlist.filter((id) => id !== product.id);
    save();
    return { saved };
  }
  const moveMatch = path.match(/^\/demo\/wishlist\/(\d+)\/move$/);
  if (moveMatch && method === "POST") {
    requireUser();
    const product = findProduct(moveMatch[1]);
    if (!product || product.stock < 1) throw new Error("This item is currently out of stock.");
    const existing = state.cart.find((item) => item.id === product.id);
    const quantity = (existing?.quantity || 0) + 1;
    if (quantity > product.stock) throw new Error("There isn't enough stock for that quantity.");
    state.cart = [...state.cart.filter((item) => item.id !== product.id), { ...product, quantity, line_total: Math.round(product.discounted_price * quantity * 100) / 100 }];
    state.wishlist = state.wishlist.filter((id) => id !== product.id);
    save();
    return { ok: true };
  }
  const wishlistMatch = path.match(/^\/demo\/wishlist\/(\d+)$/);
  if (wishlistMatch && method === "DELETE") {
    requireUser();
    state.wishlist = state.wishlist.filter((id) => id !== Number(wishlistMatch[1]));
    save();
    return { ok: true };
  }
  if (method === "GET" && path === "/demo/doctors") return { doctors: DOCTORS };
  if (method === "GET" && path === "/demo/appointments" && params.has("slots")) {
    requireUser();
    const doctor = params.get("doctor");
    const selectedDate = params.get("date");
    const day = new Date(`${selectedDate}T12:00:00`);
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    if (!DOCTORS.some((entry) => entry.name === doctor) || Number.isNaN(day.getTime()) || day <= today || day > new Date(today.getTime() + 30 * 86400000) || day.getDay() === 0 || day.getDay() === 6) {
      throw new Error("Choose a weekday within the next 30 days.");
    }
    const booked = new Set(state.appointments.filter((item) => item.doctor_name === doctor && item.appointment_at.startsWith(selectedDate) && item.status !== "cancelled").map((item) => item.appointment_at.slice(-5)));
    const slots = [];
    for (let hour = 10; hour < 17; hour++) {
      if (hour === 13) continue;
      for (const minute of [0, 30]) {
        const slot = `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
        if (!booked.has(slot)) slots.push(slot);
      }
    }
    return { date: selectedDate, doctor, slots };
  }
  if (method === "GET" && path === "/demo/appointments") {
    requireUser();
    return { appointments: [...state.appointments].sort((a, b) => b.appointment_at.localeCompare(a.appointment_at)) };
  }
  if (method === "POST" && path === "/demo/appointments") {
    requireUser();
    const appointmentAt = String(body.appointmentAt || "");
    const [selectedDate, selectedTime] = appointmentAt.split(" ");
    const day = new Date(`${selectedDate}T12:00:00`);
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const validTime = /^(1[0-2]|1[4-6]):(00|30)$/.test(selectedTime || "");
    if (!DOCTORS.some((entry) => entry.name === body.doctor) || Number.isNaN(day.getTime()) || day <= today || day > new Date(today.getTime() + 30 * 86400000) || day.getDay() === 0 || day.getDay() === 6 || !validTime) {
      throw new Error("Choose an available weekday and time.");
    }
    const conflict = state.appointments.some((item) => item.doctor_name === body.doctor && item.appointment_at === appointmentAt && item.status !== "cancelled");
    if (conflict) throw new Error("That demo slot is already taken. Choose another time.");
    const appointment = { id: Date.now(), doctor_name: body.doctor, appointment_at: appointmentAt, status: "demo", notes: String(body.notes || "").slice(0, 500) };
    state.appointments.push(appointment);
    save();
    return { appointment };
  }
  const appointmentMatch = path.match(/^\/demo\/appointments\/(\d+)$/);
  if (appointmentMatch && method === "DELETE") {
    requireUser();
    const appointment = state.appointments.find((item) => item.id === Number(appointmentMatch[1]));
    if (!appointment) throw new Error("That demo appointment could not be found.");
    appointment.status = "cancelled";
    save();
    return { ok: true };
  }
  throw new Error("That demo action is not available.");
}
function toast(message) {
  const node = $("#toast"); node.textContent = message; node.classList.add("show");
  clearTimeout(state.toastTimer); state.toastTimer = setTimeout(() => node.classList.remove("show"), 2800);
}
function categoryIcon(category) { return categoryEmojis[category] || "✳"; }
function renderCategories() {
  $("#categoryRow").innerHTML = ["All", ...state.categories].map((category) => `<button class="category-tile ${getCategory() === category ? "active" : ""}" data-category="${escapeHtml(category)}"><span>${category === "All" ? "✳" : categoryIcon(category)}</span><b>${escapeHtml(category === "All" ? "Shop all" : category)}</b></button>`).join("");
}
function getCategory() { return new URLSearchParams(location.hash.split("?")[1] || "").get("category") || "All"; }
function renderBrands() {
  const select = $("#brandFilter"); const selected = select.value;
  select.innerHTML = `<option value="All">All brands</option>` + state.brands.map((brand) => `<option value="${escapeHtml(brand)}">${escapeHtml(brand)}</option>`).join("");
  select.value = state.brands.includes(selected) ? selected : "All";
}
function productCard(product) {
  const saved = state.wishlist.includes(product.id);
  const cartItem = state.cart.find((item) => item.id === product.id);
  const discounted = product.discount_percent > 0;
  return `<article class="product-card" style="animation-delay:${Math.min(product.id % 8, 6) * 35}ms">
    <div class="product-image" style="--product-bg:${escapeHtml(product.color)}">
      ${product.badge ? `<span class="product-badge">${escapeHtml(product.badge)}</span>` : ""}
      <button class="heart-button ${saved ? "saved" : ""}" data-action="wishlist" data-id="${product.id}" aria-label="${saved ? "Remove from" : "Add to"} wishlist"><span>${saved ? "♥" : "♡"}</span></button>
      ${productShape(product)}
    </div>
    <div class="product-meta"><div class="product-brand">${escapeHtml(product.brand)} · ${escapeHtml(product.pack_size)}</div>
      <div class="product-title-row"><div class="product-title">${escapeHtml(product.name)}</div><div class="product-rating">★ ${Number(product.rating).toFixed(1)} <span>(${product.review_count})</span></div></div>
      <p class="product-description">${escapeHtml(product.description)}</p>
      <div class="product-purchase"><div class="product-price"><b>${money(product.discounted_price)}</b>${discounted ? `<del>${money(product.price)}</del><small>${product.discount_percent}% off</small>` : ""}</div>
      ${cartItem ? `<div class="card-quantity" aria-label="${cartItem.quantity} in bag"><button data-action="decrease" data-id="${product.id}" aria-label="Remove one ${escapeHtml(product.name)}">−</button><span>${cartItem.quantity} in bag</span><button data-action="increase" data-id="${product.id}" aria-label="Add one ${escapeHtml(product.name)}" ${cartItem.quantity >= product.stock ? "disabled" : ""}>＋</button></div>` : `<button class="add-button" data-action="cart" data-id="${product.id}" ${product.stock < 1 ? "disabled" : ""}>${product.stock < 1 ? "Sold out" : "＋ Quick add"}</button>`}</div>
    </div>
  </article>`;
}
function filters() {
  const params = new URLSearchParams({ search: $("#searchInput").value.trim(), category: getCategory(), brand: $("#brandFilter").value, maxPrice: $("#priceFilter").value, rating: $("#ratingFilter").value, available: String($("#stockFilter").checked), sort: $("#sortFilter").value });
  return params;
}
async function loadProducts() {
  try {
    const data = await demoRequest(`/demo/products?${filters().toString()}`);
    state.categories = data.categories; state.brands = data.brands;
    renderCategories(); renderBrands();
    $("#resultCount").textContent = `${data.count} thoughtful ${data.count === 1 ? "find" : "finds"}`;
    $("#productGrid").innerHTML = data.products.map(productCard).join("");
    $("#emptyState").hidden = data.products.length > 0;
    $("#productGrid").hidden = data.products.length === 0;
    const category = getCategory();
    $("#activeCategory").hidden = category === "All";
    $("#activeCategoryName").textContent = category;
    $("#clearAllFilters").hidden = !$("#searchInput").value && category === "All" && $("#brandFilter").value === "All" && !$("#priceFilter").value && !$("#ratingFilter").value && !$("#stockFilter").checked && $("#sortFilter").value === "featured";
  } catch (error) { toast(error.message); }
}
async function loadUserState() {
  const data = await demoRequest("/demo/me"); state.user = data.user;
  $("#accountLabel").textContent = state.user ? state.user.name.split(" ")[0] : "Sign in";
  $("#accountButton").setAttribute("aria-label", state.user ? "Open your account" : "Sign in");
  if (state.user) {
    const [cart, wishlist] = await Promise.all([demoRequest("/demo/cart"), demoRequest("/demo/wishlist")]);
    state.cart = cart.items; state.wishlist = wishlist.items.map((item) => item.id);
  } else { state.cart = []; state.wishlist = []; }
  updateCounts();
}
function updateCounts() {
  $("#cartCount").textContent = state.cart.reduce((sum, item) => sum + item.quantity, 0);
  $("#wishlistCount").textContent = state.wishlist.length;
}
function openAuth(mode = "login") {
  if (state.user) { openProfile(); return; }
  setAuthMode(mode); $("#authError").textContent = ""; $("#authBackdrop").classList.add("open"); document.body.style.overflow = "hidden";
}
function closeModals() {
  $("#authBackdrop").classList.remove("open"); $("#profileBackdrop").classList.remove("open");
  $("#appointmentBackdrop").classList.remove("open");
  if (!$("#sidePanel").classList.contains("open")) document.body.style.overflow = "";
}
function setAuthMode(mode) {
  state.authMode = mode;
  document.querySelectorAll(".auth-tab").forEach((tab) => tab.classList.toggle("active", tab.dataset.mode === mode));
  $("#nameField").hidden = mode !== "register"; $("#mobileField").hidden = mode !== "register";
  $("#authTitle").textContent = mode === "register" ? "A warm welcome." : "Welcome home.";
  $("#authIntro").textContent = mode === "register" ? "Create a sample profile. It stays in this browser only." : "Preview the shop with a sample sign-in. No password is checked or sent.";
  $("#authSubmit").innerHTML = mode === "register" ? `Create account <span>→</span>` : `Sign in <span>→</span>`;
  $("#passwordField").hidden = mode === "register";
  $("#authForm").elements.password.required = mode !== "register";
  $("#authForm").elements.password.autocomplete = "off";
  $("#authForm").elements.mobile.required = mode === "register";
  $("#authForm").elements.name.required = mode === "register";
}
function openProfile() {
  if (!state.user) return openAuth();
  const form = $("#profileForm");
  form.elements.name.value = state.user.name || ""; form.elements.email.value = state.user.email || "";
  form.elements.mobile.value = state.user.mobile || ""; form.elements.address.value = state.user.address || "";
  $("#profileError").textContent = "";
  $("#profileBackdrop").classList.add("open"); document.body.style.overflow = "hidden";
}
function panelItem(product, wishlistMode) {
  return `<div class="panel-item"><div class="mini-art" style="--product-bg:${escapeHtml(product.color)}">${escapeHtml(product.emoji)}</div><div class="panel-item-main"><small>${escapeHtml(product.brand)}</small><b>${escapeHtml(product.name)}</b><span>${money(product.discounted_price)} · ${escapeHtml(product.pack_size)}</span>
    <div class="panel-item-actions">${wishlistMode ? `<button data-action="move" data-id="${product.id}">Move to bag</button>` : `<div class="qty-control"><button data-action="decrease" data-id="${product.id}" aria-label="Decrease quantity">−</button><span>${product.quantity}</span><button data-action="increase" data-id="${product.id}" aria-label="Increase quantity">＋</button></div>`}<button class="remove-item" data-action="remove-${wishlistMode ? "wishlist" : "cart"}" data-id="${product.id}">Remove</button></div></div><b>${wishlistMode ? "" : money(product.line_total)}</b></div>`;
}
function openPanel(mode) {
  if (!state.user) { openAuth(); return; }
  state.panelMode = mode;
  $("#panelTitle").innerHTML = mode === "cart" ? `Your bag <span>(${state.cart.length})</span>` : `Your saved finds <span>(${state.wishlist.length})</span>`;
  $("#panelEyebrow").textContent = mode === "cart" ? "YOUR LITTLE FINDS" : "SAVED FOR A LITTLE LATER";
  const content = $("#panelContent"); const footer = $("#panelFooter");
  if (mode === "cart") {
    content.innerHTML = state.cart.length ? state.cart.map((item) => panelItem(item, false)).join("") : `<div class="panel-empty"><span>🛍️</span><h3>A little room for something good.</h3><p>Your bag is taking a breather. Find something lovely for your everyday shelf.</p><button class="button button-dark" data-action="continue-shopping">Explore the shop ↗</button></div>`;
    const subtotal = state.cart.reduce((sum, item) => sum + item.line_total, 0);
    footer.innerHTML = state.cart.length ? `<div class="panel-total"><span>Subtotal</span><b>${money(subtotal)}</b></div><button class="button button-dark panel-checkout" data-action="checkout">Continue to checkout <span>→</span></button><div class="panel-note">Shipping and taxes calculated at checkout</div>` : "";
  } else {
    const products = window.HOMOEO_PRODUCTS.filter((item) => state.wishlist.includes(item.id));
    content.innerHTML = products.length ? products.map((item) => panelItem(item, true)).join("") : `<div class="panel-empty"><span>♡</span><h3>Keep a few close.</h3><p>Tap the little heart on anything you love to save it for later.</p><button class="button button-dark" data-action="continue-shopping">Find your favourites ↗</button></div>`;
    footer.innerHTML = products.length ? `<div class="panel-note">Your saved favourites, ready whenever you are ✳</div>` : "";
  }
  $("#sidePanel").removeAttribute("inert"); $("#scrim").classList.add("open"); $("#sidePanel").classList.add("open"); $("#sidePanel").setAttribute("aria-hidden", "false"); document.body.style.overflow = "hidden"; $("#panelClose").focus();
}
function closePanel() {
  const wasOpen = $("#sidePanel").classList.contains("open");
  if (wasOpen) $(state.panelMode === "wishlist" ? "#wishlistButton" : "#cartButton").focus();
  $("#scrim").classList.remove("open"); $("#sidePanel").classList.remove("open"); $("#sidePanel").setAttribute("aria-hidden", "true");
  $("#sidePanel").setAttribute("inert", "");
  if (!$("#authBackdrop").classList.contains("open") && !$("#profileBackdrop").classList.contains("open")) document.body.style.overflow = "";
}
async function productAction(action, id) {
  const productId = Number(id);
  if (action === "cart" || action === "wishlist" || action === "move") {
    if (!state.user) {
      state.pendingProductAction = { action, productId };
      openAuth();
      toast("Sign in and we'll take care of that for you.");
      return;
    }
  }
  if (action === "cart") {
    await demoRequest("/demo/cart", { method: "POST", body: JSON.stringify({ productId }) });
    await loadUserState(); await loadProducts(); toast("A lovely pick — added to your bag."); return;
  }
  if (action === "increase" || action === "decrease") {
    const item = state.cart.find((product) => product.id === productId);
    if (!item) return;
    const quantity = item.quantity + (action === "increase" ? 1 : -1);
    if (quantity < 1) await demoRequest(`/demo/cart/${productId}`, { method: "DELETE" });
    else await demoRequest(`/demo/cart/${productId}`, { method: "PATCH", body: JSON.stringify({ quantity }) });
    await loadUserState(); await loadProducts();
    toast(quantity < 1 ? "Removed from your bag." : "Your bag is up to date.");
    return;
  }
  if (action === "wishlist") {
    const result = await demoRequest("/demo/wishlist", { method: "POST", body: JSON.stringify({ productId }) });
    updateCounts(); loadProducts(); toast(result.saved ? "Saved for a little later." : "Removed from your saved finds.");
    if ($("#sidePanel").classList.contains("open") && state.panelMode === "wishlist") openPanel("wishlist");
    return;
  }
  if (action === "move") {
    await demoRequest(`/demo/wishlist/${productId}/move`, { method: "POST", body: "{}" });
    await loadUserState(); await loadProducts(); openPanel("wishlist"); toast("Moved to your bag.");
  }
}
async function panelAction(action, id) {
  const productId = Number(id);
  if (action === "continue-shopping") { closePanel(); $("#shop").scrollIntoView({ behavior: "smooth" }); return; }
  if (action === "checkout") { toast("Frontend demo only — checkout and payment are not connected."); return; }
  if (action === "move") return productAction("move", productId);
  if (action === "remove-cart") await demoRequest(`/demo/cart/${productId}`, { method: "DELETE" });
  if (action === "remove-wishlist") await demoRequest(`/demo/wishlist/${productId}`, { method: "DELETE" });
  if (action === "increase" || action === "decrease") {
    const item = state.cart.find((product) => product.id === productId);
    if (!item) return;
    const quantity = item.quantity + (action === "increase" ? 1 : -1);
    if (quantity < 1) await demoRequest(`/demo/cart/${productId}`, { method: "DELETE" });
    else await demoRequest(`/demo/cart/${productId}`, { method: "PATCH", body: JSON.stringify({ quantity }) });
  }
  await loadUserState(); await loadProducts(); openPanel(state.panelMode);
}
function localDateString(value) {
    const year = value.getFullYear();
    const month = String(value.getMonth() + 1).padStart(2, "0");
    const day = String(value.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }
  function nextWeekday(from) {
    const next = new Date(from);
    next.setDate(next.getDate() + 1);
    while (next.getDay() === 0 || next.getDay() === 6) next.setDate(next.getDate() + 1);
    return next;
  }
  function renderAppointmentList(appointments) {
    const list = $("#appointmentList");
    if (!appointments.length) {
      list.innerHTML = `<div class="appointment-empty"><span>✿</span><p>Your upcoming visits will be right here.</p></div>`;
      return;
    }
    list.innerHTML = appointments.map((appointment) => {
      const dateTime = new Date(appointment.appointment_at.replace(" ", "T"));
      const future = dateTime > new Date();
      const statusLabel = appointment.status === "cancelled" ? "Cancelled demo" : future ? "Demo booking" : "Past demo";
      return `<article class="appointment-item"><div class="appointment-date-chip"><b>${new Intl.DateTimeFormat("en", { day: "2-digit" }).format(dateTime)}</b><span>${new Intl.DateTimeFormat("en", { month: "short" }).format(dateTime)}</span></div><div class="appointment-details"><b>${escapeHtml(appointment.doctor_name)}</b><span>${new Intl.DateTimeFormat("en", { weekday: "short", month: "short", day: "numeric" }).format(dateTime)} · ${new Intl.DateTimeFormat("en", { hour: "numeric", minute: "2-digit" }).format(dateTime)}</span><small>${statusLabel}${appointment.notes ? ` · ${escapeHtml(appointment.notes)}` : ""}</small>${appointment.status !== "cancelled" && future ? `<button class="cancel-appointment" data-cancel-appointment="${appointment.id}">Cancel demo</button>` : ""}</div></article>`;
    }).join("");
  }
  async function loadAppointmentSlots() {
    const requestId = ++state.slotRequestId;
    const grid = $("#slotGrid");
    const doctor = $("#doctorSelect").value;
    const selectedDate = $("#appointmentDate").value;
    state.selectedSlot = "";
    $("#appointmentSubmit").disabled = true;
    $("#appointmentSubmit").innerHTML = `Choose a demo time <span>→</span>`;
    if (!doctor || !selectedDate) {
      grid.innerHTML = `<p class="slot-message">Choose a doctor and day to see available times.</p>`;
      return;
    }
    grid.innerHTML = `<p class="slot-message">Checking available times…</p>`;
    try {
      const data = await demoRequest(`/demo/appointments?slots=1&doctor=${encodeURIComponent(doctor)}&date=${encodeURIComponent(selectedDate)}`);
      if (requestId !== state.slotRequestId) return;
      grid.innerHTML = data.slots.length ? data.slots.map((slot) => `<button class="slot-button" type="button" data-slot="${slot}" aria-pressed="false">${slot}</button>`).join("") : `<p class="slot-message">No times available on this day. Try another weekday.</p>`;
    } catch (error) {
      if (requestId !== state.slotRequestId) return;
      grid.innerHTML = `<p class="slot-message">${escapeHtml(error.message)}</p>`;
    }
  }
async function openAppointments() {
    if (!state.user) { state.pendingAppointment = true; openAuth(); return; }
    state.selectedSlot = "";
    $("#appointmentError").textContent = "";
    $("#appointmentDate").min = localDateString(nextWeekday(new Date()));
    const maximumDate = new Date();
    maximumDate.setDate(maximumDate.getDate() + 30);
    $("#appointmentDate").max = localDateString(maximumDate);
    $("#appointmentDate").value = $("#appointmentDate").min;
    $("#appointmentBackdrop").classList.add("open");
    document.body.style.overflow = "hidden";
    try {
      const [doctorData, appointmentData] = await Promise.all([demoRequest("/demo/doctors"), demoRequest("/demo/appointments")]);
      state.doctors = doctorData.doctors;
      $("#doctorSelect").innerHTML = state.doctors.map((doctor) => `<option value="${escapeHtml(doctor.name)}">${escapeHtml(doctor.name)} · ${escapeHtml(doctor.specialty)}</option>`).join("");
      renderAppointmentList(appointmentData.appointments);
      await loadAppointmentSlots();
      $("#doctorSelect").focus();
    } catch (error) {
      $("#appointmentError").textContent = error.message;
    }
}
$("#categoryRow").addEventListener("click", (event) => {
  const tile = event.target.closest("[data-category]"); if (!tile) return;
  const category = tile.dataset.category;
  history.replaceState(null, "", category === "All" ? "#shop" : `#shop?category=${encodeURIComponent(category)}`);
  loadProducts(); $("#shop").scrollIntoView({ behavior: "smooth" });
});
let searchTimer;
$("#searchInput").addEventListener("input", () => { clearTimeout(searchTimer); searchTimer = setTimeout(loadProducts, 200); });
["brandFilter", "priceFilter", "ratingFilter", "stockFilter", "sortFilter"].forEach((id) => $(`#${id}`).addEventListener("change", loadProducts));
$("#clearFilters").addEventListener("click", () => {
  $("#searchInput").value = ""; $("#brandFilter").value = "All"; $("#priceFilter").value = ""; $("#ratingFilter").value = ""; $("#stockFilter").checked = false; $("#sortFilter").value = "featured";
  history.replaceState(null, "", "#shop"); loadProducts();
});
$("#clearAllFilters").addEventListener("click", () => {
  $("#searchInput").value = ""; $("#brandFilter").value = "All"; $("#priceFilter").value = ""; $("#ratingFilter").value = ""; $("#stockFilter").checked = false; $("#sortFilter").value = "featured";
  history.replaceState(null, "", "#shop"); loadProducts();
});
$("#clearCategory").addEventListener("click", () => { history.replaceState(null, "", "#shop"); loadProducts(); });
$("#productGrid").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-action]"); if (!button) return;
  button.disabled = true;
  try { await productAction(button.dataset.action, button.dataset.id); } catch (error) { toast(error.message); } finally { button.disabled = false; }
});
$("#panelContent").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-action]"); if (!button) return;
  button.disabled = true;
  try { await panelAction(button.dataset.action, button.dataset.id); } catch (error) { toast(error.message); } finally { button.disabled = false; }
});
$("#accountButton").addEventListener("click", () => state.user ? openProfile() : openAuth());
$("#cartButton").addEventListener("click", () => openPanel("cart"));
$("#wishlistButton").addEventListener("click", () => openPanel("wishlist"));
$("#panelClose").addEventListener("click", closePanel);
$("#scrim").addEventListener("click", closePanel);
$("#authClose").addEventListener("click", closeModals);
$("#profileClose").addEventListener("click", closeModals);
$("#appointmentClose").addEventListener("click", closeModals);
$("#bookAppointment").addEventListener("click", openAppointments);
$("#bookAppointmentBanner").addEventListener("click", openAppointments);
$("#authBackdrop").addEventListener("click", (event) => { if (event.target === $("#authBackdrop")) closeModals(); });
$("#profileBackdrop").addEventListener("click", (event) => { if (event.target === $("#profileBackdrop")) closeModals(); });
$("#appointmentBackdrop").addEventListener("click", (event) => { if (event.target === $("#appointmentBackdrop")) closeModals(); });
$("#doctorSelect").addEventListener("change", loadAppointmentSlots);
$("#appointmentDate").addEventListener("change", loadAppointmentSlots);
$("#slotGrid").addEventListener("click", (event) => {
  const slot = event.target.closest("[data-slot]");
  if (!slot) return;
  state.selectedSlot = slot.dataset.slot;
  $("#slotGrid").querySelectorAll(".slot-button").forEach((button) => {
    button.classList.toggle("selected", button === slot);
    button.setAttribute("aria-pressed", String(button === slot));
  });
  $("#appointmentSubmit").disabled = false;
  $("#appointmentSubmit").innerHTML = `Save demo booking <span>→</span>`;
});
$("#appointmentForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.selectedSlot) return;
  const form = new FormData(event.currentTarget);
  const submit = $("#appointmentSubmit");
  submit.disabled = true;
  $("#appointmentError").textContent = "";
  try {
    await demoRequest("/demo/appointments", {
      method: "POST",
      body: JSON.stringify({
        doctor: form.get("doctor"),
        appointmentAt: `${form.get("date")} ${state.selectedSlot}`,
        notes: form.get("notes"),
      }),
    });
    const data = await demoRequest("/demo/appointments");
    renderAppointmentList(data.appointments);
    await loadAppointmentSlots();
    toast("Demo booking saved in this browser only. No clinic was contacted.");
  } catch (error) {
    $("#appointmentError").textContent = error.message;
    await loadAppointmentSlots();
  }
});
$("#appointmentList").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-cancel-appointment]");
  if (!button) return;
  button.disabled = true;
  try {
    await demoRequest(`/demo/appointments/${button.dataset.cancelAppointment}`, { method: "DELETE" });
    const data = await demoRequest("/demo/appointments");
    renderAppointmentList(data.appointments);
    await loadAppointmentSlots();
    toast("Demo booking removed from this browser.");
  } catch (error) {
    button.disabled = false;
    toast(error.message);
  }
});
document.querySelectorAll(".auth-tab").forEach((tab) => tab.addEventListener("click", () => { setAuthMode(tab.dataset.mode); $("#authError").textContent = ""; }));
$("#authForm").addEventListener("submit", async (event) => {
  event.preventDefault(); const authForm = event.currentTarget; const form = new FormData(authForm); const mode = state.authMode;
  $("#authError").textContent = "";
  const payload = mode === "register" ? { name: form.get("name"), email: form.get("email"), mobile: form.get("mobile") } : { email: form.get("email"), password: form.get("password") };
  const button = $("#authSubmit"); button.disabled = true;
  try {
    await demoRequest(`/demo/${mode === "register" ? "register" : "login"}`, { method: "POST", body: JSON.stringify(payload) });
    authForm.reset(); closeModals(); await loadUserState(); await loadProducts(); toast(mode === "register" ? "Your little corner is ready. Welcome!" : "Welcome back. We're glad you're here.");
    if (state.pendingProductAction) {
      const pendingAction = state.pendingProductAction;
      state.pendingProductAction = null;
      await productAction(pendingAction.action, pendingAction.productId);
    }
    if (state.pendingAppointment) { state.pendingAppointment = false; await openAppointments(); }
  } catch (error) { $("#authError").textContent = error.message; }
  finally { button.disabled = false; }
});
$("#profileForm").addEventListener("submit", async (event) => {
  event.preventDefault(); const form = new FormData(event.currentTarget);
  try {
    const data = await demoRequest("/demo/profile", { method: "PATCH", body: JSON.stringify({ name: form.get("name"), mobile: form.get("mobile"), address: form.get("address") }) });
    state.user = data.user; state.savedProfile = data.user; $("#accountLabel").textContent = state.user.name.split(" ")[0]; $("#profileError").textContent = ""; toast("Your demo profile is saved in this browser.");
  } catch (error) { $("#profileError").textContent = error.message; }
});
$("#signOut").addEventListener("click", async () => {
  try { await demoRequest("/demo/logout", { method: "POST", body: "{}" }); closeModals(); await loadUserState(); await loadProducts(); toast("You've been signed out. Take care."); }
  catch (error) { toast(error.message); }
});
document.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") { event.preventDefault(); $("#searchInput").focus(); }
  if (event.key === "Escape") { closePanel(); closeModals(); }
});
(async function start() {
  try { restoreDemoState(); await loadUserState(); await loadProducts(); }
  catch (error) { toast(error.message); }
})();
