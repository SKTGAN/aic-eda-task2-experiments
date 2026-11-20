"""Compare two validated loss programs on one fixed CPU fixture. No physical scoring."""
import ast
import math


def compare(parent, candidate):
    try:
        import torch
        import torch.nn.functional as F
    except ImportError:
        return {"status":"unavailable", "reason":"torch unavailable"}
    try:
        def measure(source):
            fn = next(n for n in ast.parse(source).body if getattr(n,"name",None)=="compute_tp_gnn_loss")
            scope = {"__builtins__":{"abs":abs,"float":float,"int":int,"len":len,"max":max,"min":min},
                     "torch":torch,"F":F}
            exec(compile(ast.Module(body=[fn],type_ignores=[]),"<validated loss>","exec"),scope)
            idx = torch.arange(24,dtype=torch.long)
            groups = torch.arange(96,dtype=torch.float32).reshape(24,4)
            emb = F.normalize(torch.sin(groups*0.37)+torch.cos(groups*0.11),dim=1).requires_grad_()
            pos,neg = (idx+1)%24,(idx+13)%24
            target = (idx*5+3)%24
            dots = lambda a,b:(emb[a]*emb[b]).sum(1)
            areas = 1+(idx%4).float()
            weights = 1+(idx%7).float()
            features = torch.sin(torch.arange(240,dtype=torch.float32).reshape(24,10)*0.13)
            value = scope[fn.name](dots(idx,pos),dots(idx,neg),emb,idx,pos,idx,neg,24,1,10,
                dots(idx,target),idx,target,idx,weights,weights,features,areas)
            grad = torch.autograd.grad(value,emb)[0].detach()
            if not torch.isfinite(grad).all() or not math.isfinite(value.item()):
                raise ValueError("non-finite synthetic loss or gradient")
            return value.item(),grad
        a,g = measure(parent); b,h = measure(candidate)
        return {"status":"measured","fixture":"24 synthetic embeddings, one CPU batch",
                "parent_loss":a,"candidate_loss":b,"parent_gradient_norm":g.norm().item(),
                "candidate_gradient_norm":h.norm().item(),"gradient_difference_norm":(h-g).norm().item()}
    except (ValueError,RuntimeError,TypeError,IndexError,KeyError,NameError,AttributeError,ArithmeticError) as exc:
        return {"status":"inconclusive","reason":str(exc)[:200]}
