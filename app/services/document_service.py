import modal

f = modal.Function.lookup('docling', 'process')
f.remote()
