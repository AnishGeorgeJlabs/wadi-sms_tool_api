from django.conf.urls import url, patterns
from . import api
from httpproxy.views import HttpProxy
from . import newJobApi, blockApi, toolApi, credentialsApi, segmentationApi, dashboardApi

urlpatterns = patterns(
    '',
    url(r'^$', api.test, name='test'),
    url(r'^hproxy/(?P<url>.*)$', HttpProxy.as_view(base_url='http://hymnary.org/')),

    url(r'^query', toolApi.get_pipeline, name='query'),
    url(r'^job_update', toolApi.job_update, name='job_update'),

    url(r'^block_list/block', blockApi.block, name='block'),
    url(r'^block_list/upload', blockApi.block_list_csv, name='block_upload'),
    url(r'^block_list/count', blockApi.get_counts, name='block_count'),
    url(r'^block_list', blockApi.get_blocked, name='get_blocked'),

    url(r'^interface/login$', credentialsApi.login, name='interface.login'),

    url(r'^interface/job/new$', newJobApi.form_post, name='interface.post'),
    url(r'^interface/job/cancel$', dashboardApi.cancel_job, name='interface.cancel'),
    url(r'^interface/job/segment/new$', segmentationApi.post_segment_form, name='interface.segment'),
    url(r'^interface/job/segments$', segmentationApi.get_segment_jobs, name='interface.segment_all'),
    url(r'^interface/job/testing_message$', newJobApi.schedule_testing_send, name='interface.post_test'),

    url(r'^interface/form$', newJobApi.get_form_data, name='interface.form'),
    url(r'^interface/jobs$', newJobApi.get_jobs, name='interface.jobs'),
    url(r'^interface/dummy/form$', newJobApi.get_sample_form_data, name='interface.sample_form'),
    url(r'^configuration/(?P<namespace>\w+)/(?P<key>.*)$', api.get_conf, name='configurations'),
)
