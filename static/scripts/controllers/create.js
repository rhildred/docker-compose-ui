'use strict';

/**
 * @ngdoc function
 * @name composeUiApp.controller:CreateCtrl
 * @description
 * # CreateCtrl
 * Controller of the composeUiApp
 */
angular.module('composeUiApp')
    .controller('CreateCtrl', function ($scope, $routeParams, $resource, $location) {
        $scope.username = sUserName;
        var isEdit = $location.path().indexOf('/edit/') === 0;

        if (isEdit) {
            $scope.name = $routeParams.from;
            $scope.isEdit = true;
        }

        var Projects = $resource('api/v1/projects', null, {

            'createProject': {
                url: 'api/v1/create-project',
                method: 'POST'
            },
            'updateProject': {
                url: 'api/v1/update-project',
                method: 'PUT'
            },
            'loadProject': {
                url: 'api/v1/projects/yml/:id',
                method: 'GET'
            }
        });

        var Search = $resource('api/v1/search');
        var Yml = $resource('api/v1/yml');

        var ComposeRegistry = $resource('api/v1/compose-registry');

        ComposeRegistry.get(function (data) {
            var url = data.url;
            $scope.composeRegistry = url;
            if (url) {
                $scope.search('yml');
            }
        });

        $scope.createProject = function (name, repoName, webhookurl, env) {

            //TODO: check if name is alphanumeric
            //add our special string to the env

            name += "-" + sUserName
            var sHostName = window.location.hostname.replace("apps", name);
            var sPort = crc16(sHostName);
            var sEnv = "RHPORT=" + sPort + "\n";
            if (env) {
                sEnv += env;
            }
            console.log("host is " + sHostName + " port is " + sPort);

            Projects[isEdit ? 'updateProject' : 'createProject']({
                name: name,
                repoName: repoName,
                webhookurl, webhookurl,
                env: sEnv
            }, function (data) {
                alertify.success((isEdit ? 'updated project' : 'created project: ') + name + ', path: ' + data.path);
                $scope.$parent.reload(false);
                $location.path('project/' + name);

            }, function (err) {
                alertify.alert(err.data);
            });


        };

        // pre-fill a project's details
        $scope.loadProject = function (projectId) {

            Projects.loadProject({ id: projectId }, function (data) {
                if ('yml' in data) {
                    $scope.yml = data.yml;
                }
                if ('env' in data) {
                    $scope.env = data.env;
                }
            }, function (err) {
                alertify.alert(err.data);
            });

        };

        if ('from' in $routeParams) {
            $scope.loadProject($routeParams.from);
        }


        $scope.search = function (query) {

            Search.save({
                query: query
            }, function (res) {
                $scope.items = res.items;
            }, function (res) {
                alertify.alert('search error: ' + res.data.error);
            });

        };



        $scope.load = function (name, id) {

            Yml.save({
                id: id
            }, function (data) {
                $scope.yml = data.content;
            });
            $scope.name = name;
            $scope.items = [];
        };

        $scope.webhookurl = function () {
            return window.location.href.replace("#/create", "webhooks/" + $scope.name);
        }


    }).directive("regExInput", function(){
        "use strict";
        return {
            restrict: "A",
            require: "?regEx",
            scope: {},
            replace: false,
            link: function(scope, element, attrs, ctrl){
              element.bind('keypress', function (event) {
                var regex = new RegExp(attrs.regEx);
                var key = String.fromCharCode(!event.charCode ? event.which : event.charCode);
                if (!regex.test(key)) {
                   event.preventDefault();
                   return false;
                }
              });
            }
        };
    });
    