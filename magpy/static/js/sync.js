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

        initial: function () {
            var info, callback, success;
            success = function(info) {
                SYNC.update_existing_object_stores(info);
                SYNC.create_missing_object_stores(info);
            };

            callback = function(state) {
                SYNC.call_check_for_object_stores(state, success);
            };
            SYNC.get_state({success: callback})
            return "OK";
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
                    missing: [],
                    state: state.state}

            // Check for meta
            if (db.objectStoreNames.contains('_meta')) {
                info._meta = 1;
            } else {
                info._meta = 0;
            }

            // Check for resources
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

        update_meta_states: function (info) {
            console.log('hello zeth 123.');
            var db;
            var request = indexedDB.open(LOCAL_DB_NAME);
            request.onerror = function(event) {
                alert("Why didn't you allow my web app to use IndexedDB?!");
            };
            request.onsuccess = function(event) {
                db = request.result;
                var transaction = db.transaction(["_meta"], "readwrite");
                var object_store = transaction.objectStore("_meta");
                transaction.oncomplete = function(event) {
                    console.log("Meta transaction complete.");
                };
                var store_request = object_store.get("state");
                store_request.onerror = function(event) {
                    // Handle errors!
                    console.log("Could not find if state exists or not.");
                };
                store_request.onsuccess = function(event) {
                    var state, resource;
                    // Do something with the request.result!
                    if (typeof store_request.result == "undefined") {
                        state = {'_id': 'state'}
                    } else {
                        state = store_request.result;
                    }
                    for (resource in info.state) {
                        if (info.state.hasOwnProperty(resource)) {
                            state[resource] = info.state[resource];
                        }
                    };
                    var update_request = object_store.put(state)
                    update_request.onsuccess = function(event) {
                        console.log('Meta State updated.');
                    };

                };
            };

        },

        do_stuff: function () {
            var request = indexedDB.open("library");
            request.onsuccess = function() {
                db = request.result;
            };
            return db
        },

        update_existing_object_stores: function(info) {
            var open_request;
            open_request = indexedDB.open(LOCAL_DB_NAME);
            open_request.onsuccess = function(event) {
                var db, resource_type, i, length, transaction;
                db = event.target.result;
                // Update resource stores that already exist
                length = info.present.length;
                for (i = 0; i < length; i += 1) {
                    resource_type = info.present[i];
                    console.log("Check for update: " + resource_type);
                    transaction = db.transaction([resource_type], "readwrite");
                    transaction.oncomplete = function(event) {
                        console.log('Updated: ' + resource_type);
                    };
                    transaction.onerror = function(event) {
                        console.log('Problems updating: ' + resource_type);
                    };

                }
            }
        },

        create_missing_object_stores: function(info) {
            var new_version, open_request, resource_type;
            new_version = info.version + 1;
            open_request = indexedDB.open(LOCAL_DB_NAME, new_version);
            open_request.onupgradeneeded = function(e) {
                var db, object_store, resource_type, i, length;
                db = e.target.result;
                // Create meta store if needed
                if (info._meta == 0) {
                    console.log('Missing _meta object store.');
                    object_store = db.createObjectStore(
                        '_meta', { keyPath: "_id" });
                    console.log('Created _meta object store.');
                }

                // Create resource stores
                length = info.missing.length;
                for (i = 0; i < length; i += 1) {
                    resource_type = info.missing[i];
                    console.log('Missing object store: ' + resource_type);
                    object_store = db.createObjectStore(
                        resource_type, { keyPath: "_id" });
                    console.log('Created object store for: ' + resource_type);
                    SYNC.get_all_instances(resource_type);
                }
            }
            console.log('Done.');
            SYNC.update_meta_states(info);
        },

        populate_instances: function (instances, resource) {
            var open_request;
            open_request = indexedDB.open(LOCAL_DB_NAME);
            open_request.onsuccess = function(e) {
                var length, i, transaction, object_store, add_request;
                console.log('Populating: ' + resource);
                db = e.target.result;
                var transaction = db.transaction([resource], "readwrite");

                transaction.oncomplete = function(event) {
                    console.log("All done!");
                };
 
                transaction.onerror = function(event) {
                    // Don't forget to handle errors!
                    console.log("Error!");
                };
 
                object_store = transaction.objectStore(resource);

                length = instances.length;
                for (i = 0; i < length; i += 1) {
                    add_request = object_store.add(instances[i]);
                    add_request.onsuccess = function(event) {
                        console.log('.');
                    };
                }
            };
            open_request.onerror = function(event) {
                alert("Database error: " + event.target.errorCode);
                console.log("Database error: " + event.target.errorCode);
            };
        },

        get_all_instances: function (resource) {
            var base_url, url, options, success;
            success = function(results) {
                SYNC.populate_instances(results.results, resource);
            }
            options = {success:success}
            base_url = MAG._STORAGE.get_data_from_storage_or_function(
                "MAG._REST.get_api_url"
            );
            url = base_url + resource + '/';
            MAG._REQUEST.request(url, options);
        },

        // End of module SYNC
    };
}());

