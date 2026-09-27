"""Browser acceptance server: reject all outbound socket connections."""
import socket
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import uvicorn

original_connect = socket.socket.connect
original_connect_ex = socket.socket.connect_ex

def guarded(original):
    def connect(self, address):
        # Windows asyncio creates an internal loopback socket pair.
        if isinstance(address, tuple) and address[0] in ('127.0.0.1', '::1'):
            return original(self, address)
        raise AssertionError('API browsing attempted an outbound connection')
    return connect

socket.socket.connect = guarded(original_connect)
socket.socket.connect_ex = guarded(original_connect_ex)
Path('.cache').mkdir(exist_ok=True)
with TemporaryDirectory(prefix='browser-state-', dir='.cache') as state_dir:
    os.environ['POKELAB_USER_DB_PATH'] = str(Path(state_dir).resolve() / 'user-state.sqlite3')
    if os.getenv('POKELAB_TEST_RESEARCH') == '1':
        # Only this network-blocked acceptance server has fake inference. There
        # is no production API/environment switch that enables canned answers.
        import json
        import httpx
        from pokelab.api import app
        from pokelab.agent_providers import Selection
        def fake(request):
            envelope=json.loads(json.loads(request.content)['messages'][1]['content'])
            selected=next(e for e in envelope['packet']['evidence'] if e['payload']['kind']=='card')
            question=envelope['packet']['request']['question']
            if question=='fixture:http429':
                return httpx.Response(429,json={'error':{'code':429}})
            answer={'version':'pokelab-research-answer-v1','outcome':'answered',
                'facts':[{'text':selected['payload']['name']+' is the selected card.', 'evidence':[selected['id']]}],
                'interpretation':[{'text':'A plausible role must be supported by printed effects and this deck composition.', 'evidence':[selected['id'],'active-deck']}],
                'limitations':['The deck creator’s intent is not established.']}
            return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(answer)},
                'finish_reason':'length' if question=='fixture:truncated' else 'stop'}],
                'usage':{'prompt_tokens':100,'completion_tokens':50}})
        app.state.research_agent.transport=httpx.MockTransport(fake)
        app.state.research_agent.selection=Selection(provider='openrouter',model='fixture/research:free')
        uvicorn.run(app,host='127.0.0.1',port=int(os.getenv('POKELAB_TEST_API_PORT','8002')))
    else:
        uvicorn.run('pokelab.api:app', host='127.0.0.1', port=int(os.getenv('POKELAB_TEST_API_PORT', '8002')))
