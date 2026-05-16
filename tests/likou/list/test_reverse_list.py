import pytest
from typing import Optional

class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

class Solution:
    def reverseList(self, head: Optional[ListNode]) -> Optional[ListNode]:
        # prev = None
        # current = head
        #
        # while current:
        #     next_node = current.next  # 保存下一个节点
        #     current.next = prev       # 反转当前节点的指针
        #     prev = current            # 移动 prev 到当前节点
        #     current = next_node       # 移动 current 到下一个节点
        #
        # return prev  # 最终 prev 将是新的头节点

        # 遍历法
        # prev = None
        # current = head
        # while current:
        #     next_node = current.next
        #     current.next = prev
        #     prev = current
        #     current = next_node
        # return prev

        # 递归法
        if head is None or head.next is None:
            return head
        front = self.reverseList(head.next)
        head.next.next = head
        head.next = None
        return front

def test_reverse_linked_list():
    s = Solution()
    node1 = ListNode(1)
    node2 = ListNode(2, node1)
    node3 = ListNode(3, node2)
    print("Original linked list:")
    node3bak = node3
    while node3bak:
        print(node3bak.val)
        node3bak = node3bak.next

    reversed_head = s.reverseList(node3)
    current = reversed_head
    print("Reversed linked list:")
    while current:
        print(current.val)
        current = current.next