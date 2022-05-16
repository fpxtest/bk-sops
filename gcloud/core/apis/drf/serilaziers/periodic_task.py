# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making 蓝鲸智云PaaS平台社区版 (BlueKing PaaS Community
Edition) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at
http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from rest_framework.fields import SerializerMethodField

import env
import ujson as json
from rest_framework import serializers
from django_celery_beat.models import PeriodicTask as CeleryTask
from django.utils.translation import ugettext_lazy as _

from gcloud.core.models import Project
from gcloud.constants import PROJECT
from gcloud.core.models import ProjectConfig
from pipeline.contrib.periodic_task.models import PeriodicTask as PipelinePeriodicTask
from gcloud.core.apis.drf.serilaziers.project import ProjectSerializer
from gcloud.periodictask.models import PeriodicTask
from gcloud.utils.drf.serializer import ReadWriteSerializerMethodField


class CeleryTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = CeleryTask
        fields = "__all__"


class PipelinePeriodicTaskSerializer(serializers.ModelSerializer):
    celery_task = CeleryTaskSerializer()
    extra_info = SerializerMethodField()

    def get_extra_info(self, obj):
        return obj.extra_info

    class Meta:
        model = PipelinePeriodicTask
        fields = [
            "celery_task",
            "name",
            "creator",
            "cron",
            "extra_info",
            "id",
            "last_run_at",
            "priority",
            "queue",
            "total_run_count",
        ]


class PeriodicTaskSerializer(serializers.ModelSerializer):

    task = PipelinePeriodicTaskSerializer()
    project = ProjectSerializer()
    last_run_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S %z", read_only=True)

    class Meta:
        model = PeriodicTask
        fields = [
            "project",
            "id",
            "task",
            "creator",
            "cron",
            "enabled",
            "last_run_at",
            "name",
            "task_template_name",
            "template_id",
            "template_source",
            "total_run_count",
            "form",
            "pipeline_tree",
        ]


class CreatePeriodicTaskSerializer(serializers.ModelSerializer):
    project = serializers.IntegerField(write_only=True)
    cron = serializers.DictField(write_only=True)
    template_source = serializers.CharField(required=False, default=PROJECT)
    pipeline_tree = ReadWriteSerializerMethodField()
    name = serializers.CharField()
    template_id = serializers.IntegerField()

    def set_pipeline_tree(self, obj):
        return {"pipeline_tree": json.loads(obj)}

    def get_pipeline_tree(self, obj):
        return json.dumps(obj.pipeline_tree)

    def validate_project(self, value):
        try:
            project = Project.objects.get(id=value)
            periodic_task_limit = env.PERIODIC_TASK_PROJECT_MAX_NUMBER
            project_config = ProjectConfig.objects.filter(project_id=project.id).only("max_periodic_task_num").first()
            if project_config and project_config.max_periodic_task_num > 0:
                periodic_task_limit = project_config.max_periodic_task_num
            if PeriodicTask.objects.filter(project__id=project.id).count() >= periodic_task_limit:
                raise serializers.ValidationError("Periodic task number reaches limit: {}".format(periodic_task_limit))
            return project
        except Project.DoesNotExist:
            raise serializers.ValidationError(_("project不存在"))

    class Meta:
        model = PeriodicTask
        fields = ["project", "cron", "name", "template_id", "pipeline_tree", "template_source"]