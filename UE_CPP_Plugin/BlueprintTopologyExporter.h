// ============================================================================
// BlueprintTopologyExporter.h
// ============================================================================
// 核心职责：将 UBlueprint 内部所有图表的节点拓扑（节点/引脚/连线）序列化为 JSON
//
// 调用链：Python (unreal) → C++ UBlueprintFunctionLibrary → UBlueprint → UEdGraph
//         → UEdGraphNode → UEdGraphPin → LinkedTo → TJsonWriter → FString
//
// 放置路径：YourProject/Source/YourProject/Public/BlueprintTopologyExporter.h
// ============================================================================

#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "BlueprintTopologyExporter.generated.h"

/**
 * 蓝图拓扑导出器
 *
 * 遍历目标蓝图的所有图表（EventGraph + FunctionGraphs），
 * 提取每个节点的引脚信息及引脚间连线，输出为结构化 JSON 字符串。
 *
 * JSON 输出结构：
 * {
 *   "blueprint_name": "BP_Ball",
 *   "graphs": [
 *     {
 *       "graph_name": "EventGraph",
 *       "graph_type": "EventGraph",
 *       "nodes": [
 *         {
 *           "node_id": "K2Node_CallFunction_0",
 *           "node_class": "K2Node_CallFunction",
 *           "node_title": "Add Torque (In Radians)",
 *           "function_name": "AddTorqueInRadians",       // 仅 CallFunction 节点
 *           "event_name": "",                             // 仅 Event 节点
 *           "variable_name": "",                          // 仅 Variable 节点
 *           "pos_x": 1024,
 *           "pos_y": 512,
 *           "comment": "",
 *           "pins": [
 *             {
 *               "pin_id": "ABC123...",
 *               "pin_name": "exec",
 *               "direction": "Input",
 *               "pin_type": "exec",
 *               "pin_category": "exec",
 *               "default_value": "",
 *               "connections": ["DEF456...", "GHI789..."]
 *             }
 *           ]
 *         }
 *       ],
 *       "connections": [
 *         { "from_pin": "ABC123...", "to_pin": "DEF456..." }
 *       ]
 *     }
 *   ]
 * }
 */
UCLASS()
class UBlueprintTopologyExporter : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()

public:
    /**
     * 导出指定蓝图的所有图表节点拓扑为 JSON 字符串。
     *
     * @param TargetBP  目标蓝图资产
     * @return          JSON 字符串（UTF-8）
     */
    UFUNCTION(BlueprintCallable, Category = "Blueprint Topology")
    static FString DumpBlueprintLogicToJson(UBlueprint* TargetBP);

private:
    /** 遍历单个 UEdGraph，提取节点和连线 */
    static TSharedPtr<FJsonObject> SerializeGraph(UEdGraph* Graph);

    /** 序列化单个 UEdGraphNode 的所有引脚 */
    static TSharedPtr<FJsonObject> SerializeNode(UEdGraphNode* Node, int32 NodeIndex);

    /** 序列化单个 UEdGraphPin */
    static TSharedPtr<FJsonObject> SerializePin(UEdGraphPin* Pin);

    /** 将 PinId 转换为短字符串标识符 */
    static FString PinIdToString(const FGuid& PinId);

    /** 提取 CallFunction 节点的目标函数名 */
    static FString GetFunctionName(UEdGraphNode* Node);

    /** 提取 Event 节点的事件名 */
    static FString GetEventName(UEdGraphNode* Node);

    /** 提取 Variable 节点的变量名 */
    static FString GetVariableName(UEdGraphNode* Node);
};
