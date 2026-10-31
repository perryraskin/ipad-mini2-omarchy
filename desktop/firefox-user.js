// J86 USB browsing profile; remove the proxy settings once native Wi-Fi is ready.
user_pref("network.proxy.type", 1);
user_pref("network.proxy.socks", "169.254.21.15");
user_pref("network.proxy.socks_port", 1080);
user_pref("network.proxy.socks_version", 5);
user_pref("network.proxy.socks_remote_dns", true);
user_pref("network.http.http3.enable", false);
user_pref("browser.cache.disk.enable", false);
user_pref("browser.cache.memory.capacity", 16384);
user_pref("dom.ipc.processCount", 1);
user_pref("dom.ipc.processCount.webIsolated", 1);
user_pref("browser.startup.page", 0);
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("browser.aboutwelcome.enabled", false);
user_pref("browser.tabs.inTitlebar", 0);
// Avoid speculative processes and first-run pages on the 1 GiB A7 board.
user_pref("dom.ipc.processPrelaunch.enabled", false);
user_pref("browser.newtabpage.enabled", false);
user_pref("browser.startup.homepage", "about:blank");
user_pref("browser.startup.homepage_override.mstone", "ignore");
user_pref("browser.startup.firstrunSkipsHomepage", true);
