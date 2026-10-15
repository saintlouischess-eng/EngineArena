"""Rating identity for accelerators, using recorded evidence, never today's hardware.

Lc0 backend syntax: https://lczero.org/blog/2019/04/backend-configuration/
Scheduler GPU groups are reservations, not device selections. Unknown selections
stay isolated from identified hardware; an installed GPU alone proves nothing.
"""
from collections import Counter
import re


CPU_BACKENDS = {'blas', 'eigen', 'eigen-fp16', 'onednn', 'onednn-cpu', 'dnnl',
                'onnx-cpu', 'tensorflow-cpu', 'random'}
MULTI_BACKENDS = {'multiplexing', 'roundrobin', 'demux', 'check'}


def model_name(value):
    return re.sub(r'^(?:NVIDIA|AMD)\s+', '', str(value).strip(), flags=re.I)


def arg_value(args, name, short=None):
    result = None
    for i, value in enumerate(args):
        value = str(value)
        if value.startswith(name + '='): result = value.partition('=')[2]
        elif value in (name, short) and i + 1 < len(args): result = str(args[i + 1])
    return result


def backend_values(options, args, evidence):
    configured = str(options.get('backend') or arg_value(args, '--backend', '-b') or '').casefold()
    # A composite backend must not be replaced with its last child's announcement.
    observed = str(evidence.get('backend') or '').casefold()
    root = str(evidence.get('root_backend') or '').casefold()
    backend = root if root in MULTI_BACKENDS else configured if configured in MULTI_BACKENDS else observed or configured
    opts = str(options.get('backendoptions') or arg_value(args, '--backend-opts', '-o') or '')
    return backend, opts


def accelerated(backend):
    return bool(re.match(r'^(?:cuda|cudnn|hip|opencl|dx12|metal|sycl|onnx-(?:cuda|trt|dml)|tensorrt)(?:$|[-_])', backend))


def gpu_candidate(body, profile=None, evidence=None):
    profile, evidence = profile or {}, evidence or {}
    backend, _ = backend_values(body.get('options', {}), body.get('args', []), evidence)
    if backend in CPU_BACKENDS: return False
    return bool(accelerated(backend) or backend in MULTI_BACKENDS or evidence.get('gpu') or
                evidence.get('gpu_models') or profile.get('gpu_group') or
                re.search(r'\b(?:lc0|leela chess zero)\b', body.get('version', ''), re.I))


def describe(body, profile, evidence, hardware, scope):
    """None preserves CPU identities byte for byte. Counts are physical devices,
    not backend instances, inference threads, CUDA cores, or scheduler slots.
    Complex/ambiguous multi-device setups deliberately remain unverified.
    """
    if not gpu_candidate(body, profile, evidence): return None
    backend, opts = backend_values(body['options'], body.get('args', []), evidence)
    composite = backend in MULTI_BACKENDS
    # Quotes can contain arbitrary text: do not interpret gpu= inside a string.
    bare = re.sub(r"\"[^\"]*\"|'[^']*'", '', opts)
    indices = sorted(set(int(x) for x in re.findall(r'(?:^|[,\(])\s*gpu\s*=\s*(\d+)\s*(?=[,\)]|$)', bare)))
    models = sorted(set(model_name(x) for x in evidence.get('gpu_models', []) if x))
    if not models and evidence.get('gpu'): models = [model_name(evidence['gpu'])]
    devices, status = [], 'unverified'
    if accelerated(backend) and models and len(models) == 1:
        devices = [{'model': models[0], 'count': 1}]; status = 'engine_reported'
    elif composite and indices:
        # Device indices only identify hardware when all selected models agree
        # with the engine's announcements. Do not map OpenCL indices to NVIDIA's.
        inventory = {str(g.get('index')): model_name(g.get('name', '')) for g in hardware.get('gpus', [])}
        selected = [inventory.get(str(i)) for i in indices]
        cuda_children = bool(re.search(r"(?:\bbackend\s*=\s*['\"]?|(?:^|[,\(])\s*)(?:cuda|cudnn)[-\w]*(?=['\",\(\)]|$)", opts))
        observations = Counter(model_name(o.get('model','')) for o in evidence.get('gpu_observations',[]))
        required = Counter(selected)
        if cuda_children and all(selected) and set(selected) == set(models) and all(observations[k]>=n for k,n in required.items()):
            devices = [{'model': k, 'count': n} for k, n in sorted(Counter(selected).items())]
            status = 'engine_reported'
    value = {'kind': 'gpu', 'backend': backend or 'unverified', 'devices': devices, 'status': status}
    if not devices:
        # Includes the actual attempt's machine snapshot, not a current hardware
        # probe. Per-tournament scope avoids merging unidentified accelerators.
        value['unverified_scope'] = scope or profile.get('id') or profile.get('path') or body.get('sha256')
        value['available_devices'] = sorted(model_name(g.get('name', '')) for g in hardware.get('gpus', []))
        value['reported_models'] = models
    return value


def network_label(body):
    hashes = [body.get('observed_network')] if body.get('observed_network') else body.get('networks', [])
    hashes = sorted(set(x for x in hashes if x))
    return 'net ' + '+'.join(x[:12] for x in hashes) if hashes else 'network unverified'


def compute_summary(body):
    compute = body.get('compute')
    if not compute:
        return {'kind': 'legacy_gpu' if gpu_candidate(body) else 'cpu', 'backend': '', 'devices': [],
                'status': 'legacy_unverified' if gpu_candidate(body) else 'configured'}
    return compute


def device_label(compute):
    return ' + '.join(f"{d['model']} ×{d['count']}" for d in compute.get('devices', [])) or 'GPU unverified'


def label(body, threads):
    compute = compute_summary(body)
    version = body.get('version', 'Unnamed engine')
    if compute['kind'] == 'legacy_gpu':
        suffix = 'legacy GPU configuration unverified'
    elif compute['kind'] == 'gpu':
        suffix = f"{network_label(body)} · {device_label(compute)} · {compute['backend']}"
    else:
        suffix = f"{threads} thread" + ('s' if threads != 1 else '') if threads else 'threads unverified'
    value = f'{version} · {suffix}'
    if body.get('limit'):
        v = body['limit']; value += f" · {v.get('nodes', v.get('depth', v.get('seconds', 'clock')))} {v['kind']}"
    return value


def continuity(body, threads):
    """GPU predecessors require the same known hardware/backend and CPU support
    threads. Networks/versions may change; measured games never transfer.
    """
    c = compute_summary(body)
    if c['kind'] == 'cpu': return {'kind': 'cpu', 'threads': threads}
    if c.get('status') != 'engine_reported': return None
    return {'kind': 'gpu', 'threads': threads, 'devices': c['devices'], 'backend': c['backend']}
