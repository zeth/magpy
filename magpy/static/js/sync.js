/*global window, document, localStorage, XMLHttpRequest, Element,
  ActiveXObject, SITE_DOMAIN, APP_NAME, MAG */
/*jslint nomen: true*/

var db;

var EXAMPLE_STATE = {
    author: "51a40ce2c6ec494fcbf56e46",
    citationwork: "50ffee9249d52407f946d879",
    comcitation: "50bcb46a49d524226a4ee08e",
    edition: "505863bf49d52476bfdd3c52",
    onlinecorpus: "5029636149d52414fc0000d4",
    series: "502962b349d52414fc0000d1",
}

var SYNC = (function () {
    "use strict";
    return {
        // body of module here
        get_version: function () {
            return "0.2";
        },

        get_state: function (options) {
            var url;
            url = 'http://' + SITE_DOMAIN + '/api/_sync/state/' + APP_NAME + '/';
            if (typeof options === "undefined") {
                options = {
                    success: function (thing) {console.log(thing);}
                };
            }
            MAG._REQUEST.request(url, options);
        },

        check_for_object_stores: function (e, state, success) {
            var resource_type, db, info;
            db = e.target.result;
            info = {version: db.version,
                    present: [],
                    missing: []}

            for (resource_type in state.state) {
                if (state.state.hasOwnProperty(resource_type)) {
                    if (db.objectStoreNames.contains(resource_type)) {
                        info.present[info.present.length] = resource_type;
                    } else {
                        info.missing[info.missing.length] = resource_type;
                    }
                }
            }
            success(info);
        },

        call_check_for_object_stores: function(state, success) {
            var open_request;
            open_request = indexedDB.open(LOCAL_DB_NAME);
            open_request.onsuccess = function(e) {
                SYNC.check_for_object_stores(e, state, success);
            };
        },

        initial: function () {
            var info, callback, success;
            success = function(whatever) {
                console.log(whatever);
            };

            callback = function(state) {
                SYNC.call_check_for_object_stores(state, success);
            };
            SYNC.get_state({success: callback})
            return "OK";
        },

        do_stuff: function () {
            var request = indexedDB.open("library");
            request.onsuccess = function() {
                db = request.result;
            };
            return db
        },

        // End of module SYNC
    };
}());

