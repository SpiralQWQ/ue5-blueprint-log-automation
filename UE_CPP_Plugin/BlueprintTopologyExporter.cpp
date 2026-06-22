// ============================================================================
// BlueprintTopologyExporter.cpp
// ============================================================================
// 放置路径：YourProject/Source/YourProject/Private/BlueprintTopologyExporter.cpp
//
// 核心链路说明（从外向内穿透 UE5 蓝图结构）：
//
//   UBlueprint                           ← Python 脚本传入的顶层蓝图对象
//     ├── UbergraphPages[]               ← 事件图数组（EventGraph / BeginPlay / Tick）
//     │     └── UEdGraph                 ← 单个图表面板
//     │           └── Nodes[]            ← UEdGraphNode 数组
//     │                 ├── Pins[]       ← UEdGraphPin 数组（每个引脚）
//     │                 │     ├── PinId          (FGuid)  引脚的全局唯一标识
//     │                 │     ├── PinName        (FName)  引脚显示名 (exec/then/ReturnValue)
//     │                 │     ├── Direction      (EGPD_Input / EGPD_Output)
//     │                 │     ├── PinType        (FEdGraphPinType) 数据类型
//     │                 │     ├── DefaultValue   (FString) 默认值文本
//     │                 │     └── LinkedTo[]     (TArray<UEdGraphPin*>) ← ★ 连线目标
//     │                 │
//     │                 └── GetNodeTitle() / GetClass()->GetName()  节点身份信息
//     │
//     └── FunctionGraphs[]               ← 自定义函数图数组 (BPI 实现、纯函数)
//
//   连线去重策略：
//     引脚 A → 引脚 B 的连线会在两个引脚上各出现一次（A.LinkedTo 含 B，B.LinkedTo 含 A）。
//     通过 TSet<FString> 记录 "APinId->BPinId" 与 "BPinId->APinId" 等价，只输出一次。
// ============================================================================

#include "BlueprintTopologyExporter.h"
#include "Engine/Blueprint.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "EdGraph/EdGraphPin.h"
#include "K2Node_CallFunction.h"
#include "K2Node_Event.h"
#include "K2Node_VariableGet.h"
#include "K2Node_VariableSet.h"
#include "K2Node_FunctionEntry.h"
#include "K2Node_Tunnel.h"
#include "Json.h"
#include "JsonUtilities.h"

// ============================================================================
// 公共入口 — Python 调用此函数传入 UBlueprint*
// ============================================================================

FString UBlueprintTopologyExporter::DumpBlueprintLogicToJson(UBlueprint* TargetBP)
{
    // ---- 防御性判空 ----
    if (!TargetBP)
    {
        return TEXT("{\"error\": \"TargetBP is null\"}");
    }

    // ---- 构建根 JSON 对象 ----
    TSharedPtr<FJsonObject> RootObj = MakeShareable(new FJsonObject);

    RootObj->SetStringField("blueprint_name", TargetBP->GetName());
    RootObj->SetStringField("package_name",  TargetBP->GetPathName());

    if (TargetBP->ParentClass)
    {
        RootObj->SetStringField("parent_class", TargetBP->ParentClass->GetName());
    }

    RootObj->SetStringField("blueprint_type",
        StaticEnum<EBlueprintType>()->GetNameStringByValue(
            static_cast<int64>(TargetBP->BlueprintType)));

    // ---- 遍历所有图表（EventGraphs + FunctionGraphs）----
    TArray<TSharedPtr<FJsonValue>> GraphsArray;

    // ① 事件图（UbergraphPages）：EventGraph / BeginPlay / Tick ...
    for (UEdGraph* Graph : TargetBP->UbergraphPages)
    {
        if (Graph)
        {
            GraphsArray.Add(MakeShareable(
                new FJsonValueObject(SerializeGraph(Graph))));
        }
    }

    // ② 自定义函数图（FunctionGraphs）：用户自定义函数、BPI 接口实现函数
    for (UEdGraph* Graph : TargetBP->FunctionGraphs)
    {
        if (Graph)
        {
            GraphsArray.Add(MakeShareable(
                new FJsonValueObject(SerializeGraph(Graph))));
        }
    }

    RootObj->SetArrayField("graphs", GraphsArray);

    // ---- 序列化为 JSON 字符串 ----
    FString OutputString;
    TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&OutputString);
    FJsonSerializer::Serialize(RootObj.ToSharedRef(), Writer);
    return OutputString;
}

// ============================================================================
// 图表序列化
// ============================================================================

TSharedPtr<FJsonObject> UBlueprintTopologyExporter::SerializeGraph(UEdGraph* Graph)
{
    TSharedPtr<FJsonObject> GraphObj = MakeShareable(new FJsonObject);

    // 基础属性
    GraphObj->SetStringField("graph_name", Graph->GetName());

    // 图类型判定：EventGraph 名字是 "EventGraph"，FunctionGraph 以 "Function " 开头
    FString GraphName = Graph->GetName();
    if (GraphName == TEXT("EventGraph"))
    {
        GraphObj->SetStringField("graph_type", TEXT("EventGraph"));
    }
    else if (GraphName.StartsWith(TEXT("Function ")))
    {
        GraphObj->SetStringField("graph_type", TEXT("FunctionGraph"));
    }
    else
    {
        GraphObj->SetStringField("graph_type", TEXT("Unknown"));
    }

    // ---- 遍历节点 ----
    TArray<TSharedPtr<FJsonValue>> NodesArray;
    TArray<TSharedPtr<FJsonValue>> ConnectionsArray;

    // 连线去重：TSet 存储 "PinIdA->PinIdB" 格式字符串
    TSet<FString> RecordedConnections;
    // 为每个节点分配唯一 ID（图内自增索引）
    int32 NodeIndex = 0;

    for (UEdGraphNode* Node : Graph->Nodes)
    {
        if (!Node)
        {
            continue;
        }

        // ---- 序列化节点 ----
        TSharedPtr<FJsonObject> NodeObj = SerializeNode(Node, NodeIndex);
        NodesArray.Add(MakeShareable(new FJsonValueObject(NodeObj)));

        // ---- 提取连线（去重）----
        for (UEdGraphPin* Pin : Node->Pins)
        {
            if (!Pin)
            {
                continue;
            }

            FString FromPinId = PinIdToString(Pin->PinId);

            for (UEdGraphPin* LinkedPin : Pin->LinkedTo)
            {
                if (!LinkedPin)
                {
                    continue;
                }

                FString ToPinId = PinIdToString(LinkedPin->PinId);

                // 去重：A→B 与 B→A 只保留一个
                FString ForwardKey  = FString::Printf(TEXT("%s->%s"), *FromPinId, *ToPinId);
                FString BackwardKey = FString::Printf(TEXT("%s->%s"), *ToPinId, *FromPinId);

                if (RecordedConnections.Contains(ForwardKey) ||
                    RecordedConnections.Contains(BackwardKey))
                {
                    continue; // 已记录，跳过
                }

                RecordedConnections.Add(ForwardKey);

                // 存入 connections 数组
                TSharedPtr<FJsonObject> ConnObj = MakeShareable(new FJsonObject);
                ConnObj->SetStringField("from_pin", FromPinId);
                ConnObj->SetStringField("to_pin",   ToPinId);
                ConnObj->SetStringField("from_pin_name", Pin->PinName.ToString());
                ConnObj->SetStringField("to_pin_name",   LinkedPin->PinName.ToString());
                ConnectionsArray.Add(MakeShareable(new FJsonValueObject(ConnObj)));
            }
        }

        ++NodeIndex;
    }

    GraphObj->SetArrayField("nodes",       NodesArray);
    GraphObj->SetArrayField("connections", ConnectionsArray);

    return GraphObj;
}

// ============================================================================
// 节点序列化
// ============================================================================

TSharedPtr<FJsonObject> UBlueprintTopologyExporter::SerializeNode(
    UEdGraphNode* Node, int32 NodeIndex)
{
    TSharedPtr<FJsonObject> NodeObj = MakeShareable(new FJsonObject);

    // 节点类名 (如 K2Node_CallFunction / K2Node_Event / K2Node_IfThenElse)
    FString NodeClass = Node->GetClass()->GetName();
    NodeObj->SetStringField("node_class", NodeClass);

    // 节点在图表内的自增 ID
    NodeObj->SetStringField("node_id",
        FString::Printf(TEXT("%s_%d"), *NodeClass, NodeIndex));

    // 节点标题 — 蓝图编辑器里用户看到的名字
    NodeObj->SetStringField("node_title",
        Node->GetNodeTitle(ENodeTitleType::ListView).ToString());

    // 坐标 — 蓝图画布上的位置（用于人工比对截图）
    NodeObj->SetNumberField("pos_x", Node->NodePosX);
    NodeObj->SetNumberField("pos_y", Node->NodePosY);

    // 节点注释（用户在蓝图里写的 ballon text）
    NodeObj->SetStringField("comment", Node->NodeComment);

    // ---- 按节点类型提取专属信息 ----
    NodeObj->SetStringField("function_name",  GetFunctionName(Node));
    NodeObj->SetStringField("event_name",     GetEventName(Node));
    NodeObj->SetStringField("variable_name",  GetVariableName(Node));

    // ---- 序列化所有引脚 ----
    TArray<TSharedPtr<FJsonValue>> PinsArray;
    for (UEdGraphPin* Pin : Node->Pins)
    {
        if (Pin)
        {
            PinsArray.Add(MakeShareable(new FJsonValueObject(SerializePin(Pin))));
        }
    }
    NodeObj->SetArrayField("pins", PinsArray);

    return NodeObj;
}

// ============================================================================
// 引脚序列化
// ============================================================================

TSharedPtr<FJsonObject> UBlueprintTopologyExporter::SerializePin(UEdGraphPin* Pin)
{
    TSharedPtr<FJsonObject> PinObj = MakeShareable(new FJsonObject);

    // 引脚全局唯一 ID
    PinObj->SetStringField("pin_id", PinIdToString(Pin->PinId));

    // 引脚显示名 (exec / then / ReturnValue / Target / ...)
    PinObj->SetStringField("pin_name", Pin->PinName.ToString());

    // 引脚方向
    PinObj->SetStringField("direction",
        Pin->Direction == EGPD_Input ? TEXT("Input") : TEXT("Output"));

    // 引脚类型大类 (exec / bool / float / object / struct / ...)
    PinObj->SetStringField("pin_category",
        Pin->PinType.PinCategory.ToString());

    // 如果是 struct 类型，记录具体 struct 名
    if (Pin->PinType.PinCategory == UEdGraphSchema_K2::PC_Struct &&
        Pin->PinType.PinSubCategoryObject.IsValid())
    {
        PinObj->SetStringField("pin_sub_category",
            Pin->PinType.PinSubCategoryObject->GetName());
    }
    // 如果是 object 类型，记录具体 class 名
    else if (Pin->PinType.PinCategory == UEdGraphSchema_K2::PC_Object &&
             Pin->PinType.PinSubCategoryObject.IsValid())
    {
        PinObj->SetStringField("pin_sub_category",
            Pin->PinType.PinSubCategoryObject->GetName());
    }
    else
    {
        PinObj->SetStringField("pin_sub_category",
            Pin->PinType.PinSubCategory.ToString());
    }

    // 是否为数组
    PinObj->SetBoolField("is_array", Pin->PinType.IsArray());

    // 是否为引用传递
    PinObj->SetBoolField("is_reference", Pin->PinType.bIsReference);

    // 是否为常量
    PinObj->SetBoolField("is_const", Pin->PinType.bIsConst);

    // 默认值（文本形式）
    PinObj->SetStringField("default_value", Pin->DefaultValue);

    // ---- 连线目标引脚 ID 列表 ----
    TArray<TSharedPtr<FJsonValue>> LinkedPinIds;
    for (UEdGraphPin* LinkedPin : Pin->LinkedTo)
    {
        if (LinkedPin)
        {
            LinkedPinIds.Add(MakeShareable(
                new FJsonValueString(PinIdToString(LinkedPin->PinId))));
        }
    }
    PinObj->SetArrayField("linked_to", LinkedPinIds);

    return PinObj;
}

// ============================================================================
// 辅助函数
// ============================================================================

FString UBlueprintTopologyExporter::PinIdToString(const FGuid& PinId)
{
    return PinId.ToString(EGuidFormats::Digits);
}

FString UBlueprintTopologyExporter::GetFunctionName(UEdGraphNode* Node)
{
    // K2Node_CallFunction → 提取被调用的函数名
    if (UK2Node_CallFunction* CallFuncNode = Cast<UK2Node_CallFunction>(Node))
    {
        if (CallFuncNode->FunctionReference.GetMemberName() != NAME_None)
        {
            return CallFuncNode->FunctionReference.GetMemberName().ToString();
        }
        // 回退：从 GetFunctionName 成员读取
        return CallFuncNode->GetFunctionName();
    }
    return TEXT("");
}

FString UBlueprintTopologyExporter::GetEventName(UEdGraphNode* Node)
{
    // K2Node_Event → 提取事件名
    if (UK2Node_Event* EventNode = Cast<UK2Node_Event>(Node))
    {
        if (EventNode->EventReference.GetMemberName() != NAME_None)
        {
            return EventNode->EventReference.GetMemberName().ToString();
        }
    }
    // K2Node_FunctionEntry (自定义函数入口) → 函数名
    if (UK2Node_FunctionEntry* FuncEntry = Cast<UK2Node_FunctionEntry>(Node))
    {
        if (FuncEntry->FunctionReference.GetMemberName() != NAME_None)
        {
            return FuncEntry->FunctionReference.GetMemberName().ToString();
        }
    }
    return TEXT("");
}

FString UBlueprintTopologyExporter::GetVariableName(UEdGraphNode* Node)
{
    // K2Node_VariableGet / K2Node_VariableSet → 提取变量名
    if (UK2Node_VariableGet* VarGet = Cast<UK2Node_VariableGet>(Node))
    {
        return VarGet->VariableReference.GetMemberName().ToString();
    }
    if (UK2Node_VariableSet* VarSet = Cast<UK2Node_VariableSet>(Node))
    {
        return VarSet->VariableReference.GetMemberName().ToString();
    }
    return TEXT("");
}
