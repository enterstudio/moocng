/*jslint vars: false, browser: true, nomen: true */
/*global MOOC:true, _, jQuery, Backbone */

// Copyright 2013 Rooter Analysis S.L.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//    http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

if (_.isUndefined(window.MOOC)) {
    window.MOOC = {};
}

(function ($, Backbone, _) {
    "use strict";

    var cleanView, successHandler;

    MOOC.ajax = {
        hostA: "/course/",
        hostB: "/teacheradmin/stats/",

        getAbsoluteUrl: function (path) {
            return MOOC.ajax.hostA + MOOC.course.get("slug") + MOOC.ajax.hostB + path;
        },

        showLoading: function () {
            $(".loading").removeClass("hide");
        },

        hideLoading: function () {
            $(".loading").addClass("hide");
        },

        showAlert: function (id) {
            var alert = $("#" + id);
            alert.removeClass("hide");
            $("body").animate({ scrollTop: alert.offset().top }, 500);
            setTimeout(function () {
                $("#" + id).addClass("hide");
            }, MOOC.alertTime);
        }
    };

    MOOC.lastView = null;

    cleanView = function () {
        if (!_.isNull(MOOC.lastView)) {
            MOOC.lastView.destroy();
            MOOC.lastView = null;
        }
    };

    successHandler = function (View, instance) {
        cleanView();
        MOOC.ajax.hideLoading();

        MOOC.lastView = new View({
            model: instance,
            el: MOOC.viewport
        });
        MOOC.lastView.render();
    };

    MOOC.App = Backbone.Router.extend({
        course: function () {
            MOOC.ajax.showLoading();
            MOOC.course.get("units").fetch({
                success: function (units, response, options) {
                    successHandler(MOOC.views.Course, MOOC.course);
                },
                error: function (units, xhr, options) {
                    cleanView();
                    MOOC.ajax.hideLoading();
                    MOOC.ajax.showAlert("generic");
                }
            });
        },

        unit: function (unit) {
            MOOC.ajax.showLoading();
            unit = unit.split("unit")[1];
            var unitObj = MOOC.course.getUnitByID(unit);
            // TODO unitObj is undefined
            unitObj.get("kqs").fetch({
                success: function (kqs, response, options) {
                    successHandler(MOOC.views.Unit, unitObj);
                },
                error: function (kqs, xhr, options) {
                    cleanView();
                    MOOC.ajax.hideLoading();
                    MOOC.ajax.showAlert("generic");
                }
            });
        },

        kq: function (unit, kq) {
            MOOC.ajax.showLoading();
            unit = unit.split("unit")[1];
            kq = kq.split("kq")[1];
            var kqObj = MOOC.course.getKQByID(unit, kq);
            // TODO kqObj is undefined
            successHandler(MOOC.views.KQ, kqObj);
        }
    });

    MOOC.init = function (courseSlug, initialData) {
        var path = window.location.pathname;
        MOOC.alertTime = 4000;
        initialData.slug = courseSlug;
        MOOC.course = new MOOC.models.Course(initialData);
        MOOC.viewport = $("#viewport")[0];

        MOOC.router = new MOOC.App();
        MOOC.router.route("", "course");
        MOOC.router.route("unit:unit", "unit");
        MOOC.router.route("unit:unit/kq:kq", "kq");

        if (path.lastIndexOf('/') < path.length - 1) {
            path += '/';
        }
        Backbone.history.start({ root: path });

        if (window.location.hash.length > 1) {
            path = window.location.hash.substring(1); // Remove #
            MOOC.router.navigate(path, { trigger: true });
        } else {
            MOOC.router.navigate("", { trigger: true });
        }
    };
}(jQuery, Backbone, _));