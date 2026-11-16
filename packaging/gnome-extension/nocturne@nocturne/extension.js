// Nocturne top-bar player for GNOME Shell 45+ (ESM).
// Install: cp -r nocturne@nocturne ~/.local/share/gnome-shell/extensions/
//          gnome-extensions enable nocturne@nocturne   (log out/in on Wayland)
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import St from 'gi://St';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

const BUS_NAME = 'org.mpris.MediaPlayer2.nocturne';
const OBJ_PATH = '/org/mpris/MediaPlayer2';

const PlayerIface = `
<node>
  <interface name="org.mpris.MediaPlayer2.Player">
    <method name="PlayPause"/><method name="Next"/><method name="Previous"/>
    <property name="PlaybackStatus" type="s" access="read"/>
    <property name="Metadata" type="a{sv}" access="read"/>
  </interface>
</node>`;
const PlayerProxy = Gio.DBusProxy.makeProxyWrapper(PlayerIface);

const STRINGS = {
    ro: {notRunning: 'Nocturne nu rulează', open: 'Deschide Nocturne', nowPlaying: 'SE REDĂ ACUM'},
    en: {notRunning: 'Nocturne is not running', open: 'Open Nocturne', nowPlaying: 'NOW PLAYING'},
    ru: {notRunning: 'Nocturne не запущен', open: 'Открыть Nocturne', nowPlaying: 'СЕЙЧАС ИГРАЕТ'},
};

function strings() {
    const lang = (GLib.get_language_names()[0] || 'ro').slice(0, 2);
    return STRINGS[lang] || STRINGS.ro;
}

const NocturneIndicator = GObject.registerClass(
class NocturneIndicator extends PanelMenu.Button {
    _init(extension) {
        super._init(0.0, 'Nocturne');
        this._extension = extension;
        this._proxy = null;

        this._icon = new St.Icon({
            gicon: Gio.icon_new_for_string(`${extension.path}/icons/moon-symbolic.svg`),
            style_class: 'system-status-icon',
        });
        this.add_child(this._icon);

        // Card
        const card = new St.BoxLayout({style_class: 'nocturne-card', vertical: false});
        this._art = new St.Bin({style_class: 'nocturne-art'});
        const texts = new St.BoxLayout({vertical: true, style_class: 'nocturne-texts', x_expand: true});
        this._label = new St.Label({text: strings().nowPlaying, style_class: 'nocturne-label'});
        this._title = new St.Label({text: strings().notRunning, style_class: 'nocturne-title'});
        this._artist = new St.Label({text: '', style_class: 'nocturne-artist'});
        texts.add_child(this._label);
        texts.add_child(this._title);
        texts.add_child(this._artist);
        card.add_child(this._art);
        card.add_child(texts);

        const controls = new St.BoxLayout({style_class: 'nocturne-controls', x_align: Clutter.ActorAlign.CENTER});
        this._prev = this._button('media-skip-backward-symbolic', () => this._call('PreviousAsync'));
        this._play = this._button('media-playback-start-symbolic', () => this._playPause(), true);
        this._next = this._button('media-skip-forward-symbolic', () => this._call('NextAsync'));
        controls.add_child(this._prev);
        controls.add_child(this._play);
        controls.add_child(this._next);

        const box = new St.BoxLayout({vertical: true, style_class: 'nocturne-popup'});
        box.add_child(card);
        box.add_child(controls);
        const item = new PopupMenu.PopupBaseMenuItem({reactive: false, can_focus: false});
        item.add_child(box);
        this.menu.addMenuItem(item);

        const open = new PopupMenu.PopupMenuItem(strings().open);
        open.connect('activate', () => Gio.AppInfo.launch_default_for_uri('nocturne://show', null));
        this.menu.addMenuItem(open);

        this._watch = Gio.bus_watch_name(Gio.BusType.SESSION, BUS_NAME, Gio.BusNameWatcherFlags.NONE,
            () => this._connect(), () => this._disconnect());
    }

    _button(iconName, callback, primary = false) {
        const button = new St.Button({
            style_class: primary ? 'nocturne-button nocturne-primary' : 'nocturne-button',
            child: new St.Icon({icon_name: iconName, icon_size: primary ? 20 : 16}),
            can_focus: true,
        });
        button.connect('clicked', callback);
        return button;
    }

    _connect() {
        this._proxy = new PlayerProxy(Gio.DBus.session, BUS_NAME, OBJ_PATH, (proxy, error) => {
            if (error)
                return;
            this._changedId = proxy.connect('g-properties-changed', () => this._update());
            this._update();
        });
    }

    _disconnect() {
        if (this._proxy && this._changedId)
            this._proxy.disconnect(this._changedId);
        this._proxy = null;
        this._update();
    }

    _call(method) {
        if (this._proxy)
            this._proxy[method]().catch(() => {});
    }

    _playPause() {
        if (this._proxy)
            this._call('PlayPauseAsync');
        else
            Gio.AppInfo.launch_default_for_uri('nocturne://play_pause', null);
    }

    _update() {
        const s = strings();
        if (!this._proxy) {
            this._title.text = s.notRunning;
            this._artist.text = '';
            this._art.style = '';
            this._play.child.icon_name = 'media-playback-start-symbolic';
            return;
        }
        const meta = this._proxy.Metadata || {};
        const get = key => (meta[key] ? meta[key].deepUnpack() : null);
        const title = get('xesam:title') || 'Nocturne';
        const artists = get('xesam:artist');
        const artUrl = get('mpris:artUrl');
        this._title.text = title;
        this._artist.text = Array.isArray(artists) ? artists.join(', ') : (artists || '');
        this._art.style = artUrl ? `background-image: url("${artUrl}"); background-size: cover;` : '';
        const playing = this._proxy.PlaybackStatus === 'Playing';
        this._play.child.icon_name = playing ? 'media-playback-pause-symbolic' : 'media-playback-start-symbolic';
    }

    destroy() {
        if (this._watch)
            Gio.bus_unwatch_name(this._watch);
        this._disconnect();
        super.destroy();
    }
});

export default class NocturneExtension extends Extension {
    enable() {
        this._indicator = new NocturneIndicator(this);
        Main.panel.addToStatusArea(this.uuid, this._indicator);
    }

    disable() {
        this._indicator?.destroy();
        this._indicator = null;
    }
}
