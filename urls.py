from django.conf.urls import url, patterns
from . import api
from httpproxy.views import HttpProxy
from . import interfaceApi, blockApi, toolApi

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

    url(r'^interface/login$', interfaceApi.login, name='interface.login'),
    url(r'^interface/post$', interfaceApi.form_post, name='interface.post'),
    url(r'^interface/post/test$', interfaceApi.test_message, name='interface.post_test'),
    url(r'^interface/form$', interfaceApi.get_form_data, name='interface.form'),
    url(r'^interface/jobs$', interfaceApi.get_jobs, name='interface.jobs'),
    url(r'^interface/dummy/form$', interfaceApi.get_sample_form_data, name='interface.sample_form'),
    url(r'^configuration/(?P<namespace>\w+)/(?P<key>.*)$', api.get_conf, name='configurations'),
)
